from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path

from pydantic import SecretStr

from agent_summary.llm_client import LLMClient, LLMClientError
from app.schemas.agent import TranslationRequest, TranslationResult
from db import get_article, get_article_content, record_usage, save_agent_result
from llm_providers import LLMProviderError, ProviderNotFoundError, get_provider
from llm_providers.base import (
    ChatCompletion,
    ChatMessage,
    ChatOptions,
    LLMProvider,
    TokenUsage,
)
from llm_providers.config import ProviderConfig, ProviderKind
from llm_providers.openai_compatible import OpenAICompatibleProvider

from .agent import TranslationAgent

logger = logging.getLogger(__name__)


class TranslationServiceError(Exception):
    """Base class for translation request failures."""


class ArticleNotFoundError(TranslationServiceError):
    """Raised when the requested article does not exist."""


class ArticleContentUnavailableError(TranslationServiceError):
    """Raised when the requested article has no usable content."""


@dataclass(slots=True)
class TranslationService:
    """Application service for loading article content and persisting translation results."""

    agent_factory: type[TranslationAgent] = TranslationAgent

    async def generate(self, request: TranslationRequest) -> TranslationResult:
        article = get_article(request.entry_id)
        if article is None:
            raise ArticleNotFoundError(request.entry_id)

        content = self._resolve_content(request.entry_id, article.reader_html)
        if not content:
            raise ArticleContentUnavailableError(request.entry_id)

        try:
            if (
                self.agent_factory is TranslationAgent
                and not request.provider
                and not request.model
                and not _use_mock_llm()
            ):
                result = await self._translate_via_legacy_client(content, request.target_lang)
            else:
                agent = self._build_agent(request)
                result = await agent.translate(
                    content=content,
                    target_lang=request.target_lang,
                    temperature=0.3,
                    bilingual=True,
                )

            translation = TranslationResult(
                entry_id=request.entry_id,
                target_lang=request.target_lang,
                translation_html=result["translated_text"],
                status="success",
                provider=result["provider"],
                model=result["model"],
            )
            save_agent_result(translation)

            usage = result.get("usage", {})
            if usage:
                from datetime import datetime

                today = datetime.now(UTC).strftime("%Y-%m-%d")
                record_usage(
                    day=today,
                    provider=result["provider"],
                    model=result["model"],
                    agent="translation",
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                )

            return translation
        except ProviderNotFoundError as exc:
            translation = TranslationResult(
                entry_id=request.entry_id,
                target_lang=request.target_lang,
                translation_html="",
                status="failure",
                provider=request.provider or "unknown",
                model=request.model or "unknown",
            )
            save_agent_result(translation)
            logger.warning("Translation provider not found for %s: %s", request.entry_id, exc)
            return translation
        except LLMProviderError as exc:
            translation = TranslationResult(
                entry_id=request.entry_id,
                target_lang=request.target_lang,
                translation_html="",
                status="failure",
                provider=request.provider or "unknown",
                model=request.model or "unknown",
            )
            save_agent_result(translation)
            logger.warning("Translation provider error for %s: %s", request.entry_id, exc)
            return translation
        except Exception as exc:
            translation = TranslationResult(
                entry_id=request.entry_id,
                target_lang=request.target_lang,
                translation_html="",
                status="failure",
                provider=request.provider or "unknown",
                model=request.model or "unknown",
            )
            save_agent_result(translation)
            logger.exception("Unexpected translation failure for %s: %s", request.entry_id, exc)
            return translation

    def _build_agent(self, request: TranslationRequest) -> TranslationAgent:
        if (
            self.agent_factory is not TranslationAgent
            and not request.provider
            and not request.model
        ):
            return _instantiate_agent(self.agent_factory)

        provider_name = (request.provider or "").strip().lower()
        if provider_name == "mock" or _use_mock_llm():
            return _instantiate_agent(self.agent_factory, use_mock=True)

        provider = _resolve_provider(request)
        if request.model:
            provider = ModelOverrideProvider(provider, request.model)
        return _instantiate_agent(self.agent_factory, provider=provider)

    def _resolve_content(self, entry_id: str, reader_html: str) -> str:
        stored_content = get_article_content(entry_id)
        if stored_content is not None:
            if stored_content.cleaned_markdown.strip():
                return stored_content.cleaned_markdown.strip()
            if stored_content.plain_text.strip():
                return stored_content.plain_text.strip()

        if reader_html.strip():
            return _strip_html(reader_html)
        return ""

    async def _translate_via_legacy_client(self, content: str, target_lang: str) -> dict:
        legacy_config = _load_translation_legacy_config()
        client = LLMClient(
            api_key=legacy_config["api_key"],
            base_url=legacy_config["base_url"],
            model=legacy_config["model"],
        )
        prompt = (
            "You are a professional translator specializing in Chinese <-> English translation. "
            "Translate the provided article content into the requested target language.\n"
            "- If the target language is English, translate every Chinese sentence into English.\n"
            "- If the target language is Chinese, translate every English sentence into Chinese.\n"
            "- Text already written in the target language must be left exactly as-is.\n"
            "- Never echo the source text back untranslated, and never answer in the "
            "source language when a translation is requested.\n\n"
            "Preserve meaning, nuance, structure, formatting, technical terms, and tone. "
            "Remove raw HTML tags and output clean readable Markdown only.\n\n"
            f"Please translate to {target_lang}:\n\n{content}"
        )
        try:
            response = await client.chat_with_usage(prompt)
        except LLMClientError as exc:
            raise LLMProviderError(exc.detail) from exc

        return {
            "translated_text": response.text,
            "provider": "legacy-env",
            "model": client.model,
            "usage": {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
            },
        }


class ModelOverrideProvider:
    """Wrap an LLMProvider while allowing the request to override the model name."""

    def __init__(self, provider: LLMProvider, model: str):
        self._provider = provider
        self._model = model

    @property
    def name(self) -> str:
        return self._provider.name

    @property
    def model(self) -> str:
        return self._model

    async def chat(self, messages, *, stream=False, options=None):
        return await self._provider.chat(messages, stream=stream, options=options)


class SummaryClientProvider:
    """Adapter that makes agent_summary's legacy LLMClient usable as an LLMProvider."""

    def __init__(self, request: TranslationRequest):
        self._client = LLMClient(model=request.model or None)
        self._provider_name = "legacy-env"

    @property
    def name(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._client.model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        options: ChatOptions | None = None,
    ) -> ChatCompletion:
        if stream:
            raise LLMProviderError("Streaming is not supported by SummaryClientProvider")

        prompt = _messages_to_prompt(messages, options=options)
        try:
            response = await self._client.chat_with_usage(prompt)
        except LLMClientError as exc:
            raise LLMProviderError(exc.detail) from exc

        return ChatCompletion(
            content=response.text,
            model=self._client.model,
            usage=TokenUsage(
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
            ),
        )


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def _use_mock_llm() -> bool:
    return False


def _resolve_provider(request: TranslationRequest) -> LLMProvider:
    provider_name = request.provider if request.provider else None
    if not provider_name:
        return SummaryClientProvider(request)

    try:
        return get_provider(provider_name)
    except ProviderNotFoundError:
        return _provider_from_legacy_env(request)


def _provider_from_legacy_env(request: TranslationRequest) -> LLMProvider:
    legacy_config = _load_translation_legacy_config()
    api_key = legacy_config["api_key"]
    if not api_key:
        raise ProviderNotFoundError("No providers configured")

    base_url = legacy_config["base_url"]
    model = (request.model or legacy_config["model"] or "ecnu-max").strip()
    config = ProviderConfig(
        name=request.provider or "legacy-env",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key),
    )
    return OpenAICompatibleProvider(config)


def _messages_to_prompt(
    messages: list[ChatMessage],
    *,
    options: ChatOptions | None = None,
) -> str:
    prompt_parts: list[str] = []
    for message in messages:
        if message.role == "system":
            prompt_parts.append(message.content.strip())
            continue
        label = "User" if message.role == "user" else "Assistant"
        prompt_parts.append(f"{label}:\n{message.content.strip()}")

    if options is not None and options.temperature is not None:
        prompt_parts.append(f"Temperature: {options.temperature}")

    return "\n\n".join(part for part in prompt_parts if part)


def _candidate_env_paths() -> list[Path]:
    home = Path.home()
    return [
        Path(__file__).parent / ".env",
        Path.cwd() / ".env",
        home / ".mercury" / ".env",
        home / ".mercury" / "agent_translation.env",
    ]


def _load_legacy_env() -> None:
    for env_path in _candidate_env_paths():
        if not env_path.exists():
            continue
        with open(env_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def _load_translation_legacy_config() -> dict[str, str]:
    env_values: dict[str, str] = {}
    for env_path in _candidate_env_paths():
        if not env_path.exists():
            continue
        with open(env_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_values.setdefault(key.strip(), value.strip())

    return {
        "api_key": env_values.get("LLM_API_KEY", "").strip(),
        "base_url": env_values.get("LLM_BASE_URL", "https://chat.ecnu.edu.cn/open/api/v1").strip(),
        "model": env_values.get("LLM_MODEL", "ecnu-max").strip(),
    }


def _instantiate_agent(agent_factory, **kwargs):
    try:
        return agent_factory(**kwargs)
    except TypeError:
        return agent_factory()
