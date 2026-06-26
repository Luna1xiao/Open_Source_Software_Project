"""Application service for article translation.

Responsible for:
1. Loading article content from database
2. Invoking translation agent with LLM provider
3. Handling errors and recording results
4. Persisting translations to database
"""

import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC

from app.schemas.agent import TranslationRequest, TranslationResult
from db import get_article, get_article_content, record_usage, save_agent_result
from llm_providers import LLMProviderError, ProviderNotFoundError, get_provider

from .agent import TranslationAgent


class TranslationServiceError(Exception):
    """Base class for translation request failures."""


class ArticleNotFoundError(TranslationServiceError):
    """Raised when the requested article does not exist."""


class ArticleContentUnavailableError(TranslationServiceError):
    """Raised when the requested article has no usable content."""


@dataclass(slots=True)
class TranslationService:
    """
    Application service for article translation.

    Orchestrates:
    - Data loading from database
    - LLM provider selection
    - Translation execution
    - Result persistence
    - Usage tracking
    """

    async def generate(self, request: TranslationRequest) -> TranslationResult:
        """
        Generate translation for an article.

        Workflow:
        1. Load article metadata
        2. Resolve content (prefer cleaned over raw)
        3. Get LLM provider
        4. Execute translation
        5. Handle errors gracefully
        6. Save result and usage to database

        Args:
            request: TranslationRequest with entry_id, target_lang, provider, model

        Returns:
            TranslationResult with translated_html and status.
            Always succeeds - status indicates success/failure

        Raises:
            ArticleNotFoundError: If article doesn't exist
            ArticleContentUnavailableError: If article has no content
        """
        # 1. Load article from database
        article = get_article(request.entry_id)
        if article is None:
            raise ArticleNotFoundError(request.entry_id)

        # 2. Resolve content - prefer cleaned markdown/text over raw HTML
        content = self._resolve_content(request.entry_id, article.reader_html)
        if not content:
            raise ArticleContentUnavailableError(request.entry_id)

        # 3. Execute translation (with error handling)
        result = await self._execute_translation(
            entry_id=request.entry_id,
            target_lang=request.target_lang,
            content=content,
            provider_name=request.provider,
            model_name=request.model,
        )

        # 4. Save result to database
        save_agent_result(result)

        return result

    async def stream_generate(self, request: TranslationRequest) -> AsyncIterator[dict]:
        article = get_article(request.entry_id)
        if article is None:
            raise ArticleNotFoundError(request.entry_id)

        content = self._resolve_content(request.entry_id, article.reader_html)
        if not content:
            raise ArticleContentUnavailableError(request.entry_id)

        async for event in self._execute_translation_stream(
            entry_id=request.entry_id,
            target_lang=request.target_lang,
            content=content,
            provider_name=request.provider,
            model_name=request.model,
        ):
            yield event

    async def _execute_translation(
        self,
        entry_id: str,
        target_lang: str,
        content: str,
        provider_name: str | None,
        model_name: str | None,
    ) -> TranslationResult:
        """
        Execute translation with error handling.

        Returns SUCCESS or FAILURE status (never raises exceptions).
        Failures are recorded in the result for frontend handling.

        Args:
            entry_id: Article ID
            target_lang: Target language
            content: Article content to translate
            provider_name: Optional provider name (uses default if None)
            model_name: Optional model name (uses provider's default if None)

        Returns:
            TranslationResult with status SUCCESS or FAILURE
        """
        try:
            # Get LLM provider (uses default if name not specified)
            provider = get_provider(name=provider_name)

            # Build agent with selected provider
            agent = TranslationAgent(provider=provider)

            # Execute translation (bilingual mode: original + translation)
            agent_result = await agent.translate(
                content=content,
                target_lang=target_lang,
                temperature=0.3,  # Lower temperature for consistency
                bilingual=True,  # 双语对照模式
            )

            # Record token usage
            from datetime import datetime
            today = datetime.now(UTC).strftime("%Y-%m-%d")
            record_usage(
                day=today,
                provider=agent_result["provider"],
                model=agent_result["model"],
                agent="translation",
                prompt_tokens=agent_result["usage"]["prompt_tokens"],
                completion_tokens=agent_result["usage"]["completion_tokens"],
            )

            # Return success result
            return TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html=agent_result["translated_text"],
                status="success",
                provider=agent_result["provider"],
                model=agent_result["model"],
            )

        except ProviderNotFoundError:
            # No provider configured
            return TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status="failure",
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )

        except LLMProviderError:
            # LLM API error (auth, network, rate limit, etc.)
            # Don't propagate - record as failure
            return TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status="failure",
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )

        except Exception:
            # Unexpected error - record as failure
            return TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status="failure",
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )

    async def _execute_translation_stream(
        self,
        entry_id: str,
        target_lang: str,
        content: str,
        provider_name: str | None,
        model_name: str | None,
    ) -> AsyncIterator[dict]:
        try:
            provider = get_provider(name=provider_name)
            agent = TranslationAgent(provider=provider)
            segments = agent.prepare_bilingual_segments(content)

            accumulated_html = ""
            total_prompt_tokens = 0
            total_completion_tokens = 0
            failed_chunks = 0
            total_chunks = 0
            resolved_segments: dict[int, str] = {}

            yield {
                "type": "start",
                "entry_id": entry_id,
                "target_lang": target_lang,
                "provider": provider.name,
                "model": provider.model,
            }

            async for chunk in agent.stream_translate_bilingual(
                content=content,
                target_lang=target_lang,
                temperature=0.3,
            ):
                total_chunks += 1
                failed_chunks += 1 if chunk["failed"] else 0
                total_prompt_tokens += chunk["prompt_tokens"]
                total_completion_tokens += chunk["completion_tokens"]
                accumulated_html = (
                    f"{accumulated_html}\n\n{chunk['html']}" if accumulated_html else chunk["html"]
                )
                resolved_segments[chunk["chunk_index"]] = chunk["html"]
                yield {
                    "type": "chunk",
                    "chunk_index": chunk["chunk_index"],
                    "delta_html": chunk["html"],
                    "translation_html": self._build_stream_preview_html(
                        segments,
                        resolved_segments,
                    ),
                    "failed": chunk["failed"],
                }

            if total_chunks and failed_chunks == total_chunks:
                raise LLMProviderError("All translation chunks failed")

            from datetime import datetime

            today = datetime.now(UTC).strftime("%Y-%m-%d")
            record_usage(
                day=today,
                provider=provider.name,
                model=provider.model,
                agent="translation",
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
            )

            result = TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html=accumulated_html,
                status="success",
                provider=provider.name,
                model=provider.model,
            )
            save_agent_result(result)
            yield {
                "type": "complete",
                "result": result.model_dump(),
            }

        except ProviderNotFoundError:
            result = TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status="failure",
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )
            save_agent_result(result)
            yield {"type": "complete", "result": result.model_dump()}

        except LLMProviderError:
            result = TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status="failure",
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )
            save_agent_result(result)
            yield {"type": "complete", "result": result.model_dump()}

        except Exception:
            result = TranslationResult(
                entry_id=entry_id,
                target_lang=target_lang,
                translation_html="",
                status="failure",
                provider=provider_name or "unknown",
                model=model_name or "unknown",
            )
            save_agent_result(result)
            yield {"type": "complete", "result": result.model_dump()}

    @staticmethod
    def _build_stream_preview_html(segments, resolved_segments: dict[int, str]) -> str:
        parts: list[str] = []
        for index, segment in enumerate(segments):
            if index in resolved_segments:
                parts.append(resolved_segments[index])
                continue

            if segment.kind == "heading":
                parts.append(segment.source_text)
            else:
                parts.append(f'<div class="bilingual-original">{segment.source_text}</div>')

        return "\n\n".join(parts)

    def _resolve_content(self, entry_id: str, reader_html: str) -> str:
        """
        Resolve article content, preferring cleaned content over raw HTML.

        Content resolution priority:
        1. Cleaned markdown (highest quality)
        2. Plain text (fallback)
        3. Stripped raw HTML (last resort)

        Args:
            entry_id: Article ID for database lookup
            reader_html: Raw HTML from feed (fallback)

        Returns:
            Best available content string, or empty string if none available
        """
        # Try to get cleaned content from database
        stored_content = get_article_content(entry_id)
        if stored_content is not None:
            if stored_content.cleaned_markdown.strip():
                return stored_content.cleaned_markdown.strip()
            if stored_content.plain_text.strip():
                return stored_content.plain_text.strip()

        # Fallback: strip raw HTML
        if reader_html.strip():
            return self._strip_html(reader_html)

        return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        """
        Simple HTML tag removal.

        Removes HTML tags and normalizes whitespace.
        Used as fallback when cleaned content unavailable.

        Args:
            html: Raw HTML string

        Returns:
            Plain text with normalized whitespace
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()
