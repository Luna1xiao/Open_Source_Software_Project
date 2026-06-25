"""Translation agent - handles article translation via LLM."""

from __future__ import annotations

import asyncio
import re

from llm_providers import (
    ChatCompletion,
    ChatMessage,
    ChatOptions,
    LLMProvider,
    LLMProviderError,
    get_provider,
)
from llm_providers.base import TokenUsage


def chunk_by_headings(text: str, max_chars: int = 4000) -> list[str]:
    """Split large documents into heading-aware chunks."""
    sections = re.split(r"(?=^#{1,3}\s)", text, flags=re.MULTILINE)

    chunks: list[str] = []
    current_chunk = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if current_chunk and len(current_chunk) + len(section) > max_chars:
            chunks.append(current_chunk.strip())
            current_chunk = section
        else:
            current_chunk = f"{current_chunk}\n\n{section}" if current_chunk else section

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    if not chunks or (len(chunks) == 1 and len(chunks[0]) > max_chars):
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if current_chunk and len(current_chunk) + len(para) > max_chars:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


class TranslationAgent:
    """
    Agent for translating article content to a target language.

    Uses configured LLM provider to perform translation.
    Supports custom provider selection and temperature control.
    Supports chunked bilingual translation for long articles.
    """

    SYSTEM_PROMPT = (
        "You are a professional translator specializing in Chinese <-> English "
        "translation. Translate the provided article content into the requested "
        "target language.\n"
        "- If the target language is English, translate every Chinese sentence into English.\n"
        "- If the target language is Chinese, translate every English sentence into Chinese.\n"
        "- Text already written in the target language must be left exactly as-is.\n"
        "- Never echo the source text back untranslated, and never answer in the "
        "source language when a translation is requested.\n\n"
        "Preserve:\n"
        "- Meaning and nuance of the original text\n"
        "- Structure and formatting (paragraphs, lists, headers, etc.)\n"
        "- Technical terms and proper nouns\n"
        "- Tone and style of the original\n"
        "- Markdown formatting (bold, italic, headers, lists, etc.)\n\n"
        "Important rules:\n"
        "- Replace image links (![...](...)) with [image] placeholder\n"
        "- Keep text links [text](url) as [text] only, remove the URL\n"
        "- Remove HTML tags like <img>, <br>, <div> etc.\n"
        "- Clean up excessive whitespace and blank lines\n"
        "- Output clean, readable Markdown only\n\n"
        "Respond with ONLY the translated text in clean Markdown format."
    )

    def __init__(self, provider: LLMProvider | None = None, use_mock: bool = False):
        if provider is not None:
            self.provider = provider
        elif use_mock:
            self.provider = MockTranslationProvider()
        else:
            self.provider = get_provider()

    async def translate_chunk(
        self,
        content: str,
        target_lang: str,
        temperature: float = 0.3,
        max_retries: int = 3,
    ) -> dict:
        """Translate a single chunk with retry-on-provider-error behavior."""
        messages = [
            ChatMessage(role="system", content=self.SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"Please translate to {target_lang}:\n\n{content}",
            ),
        ]

        options = ChatOptions(temperature=temperature)

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                completion = await self.provider.chat(messages, options=options)
                return {
                    "text": completion.content,
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                }
            except LLMProviderError as exc:
                last_error = exc
                if attempt == max_retries - 1:
                    break
                await asyncio.sleep(0.5 * (2**attempt))

        raise last_error if last_error else LLMProviderError("Translation failed")

    async def translate_whole_article(
        self,
        content: str,
        target_lang: str,
        temperature: float = 0.3,
    ) -> dict:
        """Translate the whole article in one request, summary-style."""
        messages = [
            ChatMessage(role="system", content=self.SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"Please translate to {target_lang}:\n\n{content}",
            ),
        ]
        options = ChatOptions(temperature=temperature)

        completion = await self.provider.chat(messages, options=options)
        return {
            "translated_text": completion.content,
            "provider": self.provider.name,
            "model": self.provider.model,
            "usage": {
                "prompt_tokens": completion.usage.prompt_tokens,
                "completion_tokens": completion.usage.completion_tokens,
            },
        }

    async def translate_bilingual(
        self,
        content: str,
        target_lang: str,
        temperature: float = 0.3,
    ) -> dict:
        """
        Translate into alternating original/translation blocks.

        Each markdown paragraph is translated independently so the rendered
        bilingual view stays aligned block by block.
        """
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]

        total_prompt_tokens = 0
        total_completion_tokens = 0
        bilingual_parts: list[str] = []
        failed_chunks = 0

        for para in paragraphs:
            if para.startswith("#"):
                try:
                    result = await self.translate_chunk(para, target_lang, temperature)
                    bilingual_parts.append(result["text"])
                    total_prompt_tokens += result["prompt_tokens"]
                    total_completion_tokens += result["completion_tokens"]
                except LLMProviderError:
                    failed_chunks += 1
                    bilingual_parts.append(para)
                continue

            original = f'<div class="bilingual-original">{para}</div>'
            try:
                result = await self.translate_chunk(para, target_lang, temperature)
                translated = result["text"]
                total_prompt_tokens += result["prompt_tokens"]
                total_completion_tokens += result["completion_tokens"]
            except LLMProviderError:
                failed_chunks += 1
                translated = para

            translation = f'<div class="bilingual-translation">{translated}</div>'
            bilingual_parts.append(original)
            bilingual_parts.append("")
            bilingual_parts.append(translation)
            bilingual_parts.append("")

        if paragraphs and failed_chunks == len(paragraphs):
            raise LLMProviderError("All translation chunks failed")

        return {
            "translated_text": "\n\n".join(bilingual_parts),
            "provider": self.provider.name,
            "model": self.provider.model,
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
            },
        }

    async def translate(
        self,
        content: str,
        target_lang: str,
        temperature: float = 0.3,
        bilingual: bool = False,
    ) -> dict:
        """
        Translate content to target language.
        Automatically chunks long articles by headings.
        """
        if bilingual:
            return await self.translate_bilingual(content, target_lang, temperature)

        chunks = chunk_by_headings(content, max_chars=4000)

        total_prompt_tokens = 0
        total_completion_tokens = 0
        translated_chunks: list[str] = []
        failed_chunks = 0

        for chunk in chunks:
            try:
                result = await self.translate_chunk(chunk, target_lang, temperature)
                translated_chunks.append(result["text"])
                total_prompt_tokens += result["prompt_tokens"]
                total_completion_tokens += result["completion_tokens"]
            except LLMProviderError:
                failed_chunks += 1
                translated_chunks.append(chunk)

        if chunks and failed_chunks == len(chunks):
            raise LLMProviderError("All translation chunks failed")

        return {
            "translated_text": "\n\n".join(translated_chunks),
            "provider": self.provider.name,
            "model": self.provider.model,
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
            },
        }


class MockTranslationProvider:
    """Local mock provider used when no real translation provider is configured."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock-translation"

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        options: ChatOptions | None = None,
    ) -> ChatCompletion:
        user_prompt = next(
            (
                message.content
                for message in reversed(messages)
                if message.role == "user"
            ),
            "",
        )
        match = re.match(r"Please translate to\s+(.+?):\s*\n\n([\s\S]*)", user_prompt)
        if match:
            target_lang = match.group(1).strip()
            source_text = match.group(2).strip()
        else:
            target_lang = "translated"
            source_text = user_prompt.strip()

        translated = _mock_translate_text(source_text, target_lang)
        return ChatCompletion(
            content=translated,
            model=self.model,
            usage=TokenUsage(
                prompt_tokens=max(len(source_text) // 4, 1),
                completion_tokens=max(len(translated) // 4, 1),
            ),
        )


def _mock_translate_text(source_text: str, target_lang: str) -> str:
    cleaned = source_text.strip()
    if not cleaned:
        return ""

    if cleaned.startswith("#"):
        heading_marks, _, heading_text = cleaned.partition(" ")
        translated_heading = _mock_translate_sentence(heading_text or cleaned, target_lang)
        return f"{heading_marks} {translated_heading}".strip()

    return _mock_translate_sentence(cleaned, target_lang)


def _mock_translate_sentence(text: str, target_lang: str) -> str:
    language = target_lang.strip().lower()
    if language == "english":
        return f"[Mock English] {text}"
    if language == "chinese":
        return f"[Mock Chinese] {text}"
    return f"[Mock {target_lang}] {text}"
