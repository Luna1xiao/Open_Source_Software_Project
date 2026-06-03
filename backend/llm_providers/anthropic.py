import json
from collections.abc import AsyncIterator

import httpx

from llm_providers.base import (
    AuthError,
    ChatCompletion,
    ChatMessage,
    ChatOptions,
    ModelError,
    NetworkError,
    RateLimitError,
    TokenUsage,
)
from llm_providers.config import ProviderConfig
from llm_providers.openai_compatible import map_http_error

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 1024


def map_stream_error(error: dict) -> Exception:
    message = error.get("message", "Anthropic stream error")
    error_type = error.get("type")
    if error_type in ("authentication_error", "permission_error"):
        return AuthError(message)
    if error_type == "rate_limit_error":
        return RateLimitError(message)
    if error_type == "overloaded_error":
        return NetworkError(message)
    return ModelError(message)


class AnthropicProvider:
    def __init__(
        self,
        config: ProviderConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._client = client

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def model(self) -> str:
        return self._config.model

    def _base_url(self) -> str:
        return (self._config.base_url or DEFAULT_BASE_URL).rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": DEFAULT_ANTHROPIC_VERSION,
        }
        if self._config.api_key is not None:
            secret = self._config.api_key.get_secret_value()
            if self._config.api_key_header:
                headers[self._config.api_key_header] = secret
            else:
                headers["x-api-key"] = secret
        return headers

    def _payload(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool,
        options: ChatOptions | None = None,
    ) -> dict:
        system_messages = [message.content for message in messages if message.role == "system"]
        conversation = [
            message.model_dump()
            for message in messages
            if message.role in ("user", "assistant")
        ]
        payload = {
            "model": self._config.model,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "messages": conversation,
            "stream": stream,
        }
        if system_messages:
            payload["system"] = "\n\n".join(system_messages)
        if options is not None:
            payload.update(options.for_anthropic_payload())
        return payload

    def _client_kwargs(self) -> dict[str, object]:
        return {"timeout": 120.0, "trust_env": False}

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool = False,
        options: ChatOptions | None = None,
    ) -> ChatCompletion | AsyncIterator[str]:
        if stream:
            return self._stream_chat(messages, options=options)
        return await self._complete_chat(messages, options=options)

    async def _complete_chat(
        self,
        messages: list[ChatMessage],
        *,
        options: ChatOptions | None = None,
    ) -> ChatCompletion:
        url = f"{self._base_url()}/messages"
        payload = self._payload(messages, stream=False, options=options)

        try:
            if self._client is not None:
                response = await self._client.post(url, headers=self._headers(), json=payload)
            else:
                async with httpx.AsyncClient(**self._client_kwargs()) as client:
                    response = await client.post(url, headers=self._headers(), json=payload)
        except httpx.RequestError as exc:
            raise NetworkError(str(exc)) from exc

        if response.is_error:
            raise map_http_error(response.status_code, response.text)

        try:
            data = response.json()
            content = "".join(
                block.get("text", "")
                for block in data["content"]
                if block.get("type") == "text"
            )
            if not content:
                raise ModelError("Empty completion content")
            usage_raw = data.get("usage") or {}
            return ChatCompletion(
                content=content,
                model=data.get("model", self._config.model),
                usage=TokenUsage(
                    prompt_tokens=usage_raw.get("input_tokens", 0),
                    completion_tokens=usage_raw.get("output_tokens", 0),
                ),
            )
        except (KeyError, TypeError) as exc:
            raise ModelError(f"Malformed response: {response.text}") from exc

    async def _stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        options: ChatOptions | None = None,
    ) -> AsyncIterator[str]:
        url = f"{self._base_url()}/messages"
        payload = self._payload(messages, stream=True, options=options)
        client: httpx.AsyncClient | None = self._client
        should_close_client = client is None

        try:
            if client is None:
                client = httpx.AsyncClient(**self._client_kwargs())

            async with client.stream(
                "POST",
                url,
                headers=self._headers(),
                json=payload,
            ) as response:
                if response.is_error:
                    body = await response.aread()
                    raise map_http_error(response.status_code, body.decode())

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if not data:
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("type") == "error":
                        error = chunk.get("error", {})
                        raise map_stream_error(error)
                    if chunk.get("type") != "content_block_delta":
                        continue
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        yield delta["text"]
        except httpx.RequestError as exc:
            raise NetworkError(str(exc)) from exc
        finally:
            if should_close_client and client is not None:
                await client.aclose()
