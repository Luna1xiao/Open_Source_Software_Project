from collections.abc import AsyncIterator
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ChatCompletion(BaseModel):
    content: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)


class ChatOptions(BaseModel):
    temperature: float | None = None
    max_completion_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None

    def for_openai_payload(self) -> dict[str, float | int]:
        return {
            key: value
            for key, value in self.model_dump(exclude_none=True).items()
            if value is not None
        }

    def for_anthropic_payload(self) -> dict[str, float | int]:
        payload: dict[str, float | int] = {}
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.max_completion_tokens is not None:
            payload["max_tokens"] = self.max_completion_tokens
        if self.top_p is not None:
            payload["top_p"] = self.top_p
        return payload

    def for_ollama_payload(self) -> dict[str, dict[str, float]]:
        options: dict[str, float] = {}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.top_p is not None:
            options["top_p"] = self.top_p
        if not options:
            return {}
        return {"options": options}


class LLMProviderError(Exception):
    """Base class for provider failures."""


class AuthError(LLMProviderError):
    """Invalid or missing credentials."""


class NetworkError(LLMProviderError):
    """Transport or connectivity failure."""


class RateLimitError(LLMProviderError):
    """Provider rejected the request due to rate limits."""


class ModelError(LLMProviderError):
    """Unknown model, provider kind, or malformed provider response."""


class ProviderNotFoundError(LLMProviderError):
    """No provider matches the requested name."""


@runtime_checkable
class LLMProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        options: ChatOptions | None = None,
    ) -> ChatCompletion | AsyncIterator[str]: ...
