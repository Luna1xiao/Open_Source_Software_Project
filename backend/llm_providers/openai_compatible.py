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

DEFAULT_BASE_URL = "https://api.openai.com/v1"


def map_http_error(status_code: int, detail: str) -> Exception:
    if status_code in (401, 403):
        return AuthError(detail)
    if status_code == 429:
        return RateLimitError(detail)
    if status_code == 404:
        return ModelError(detail)
    if status_code >= 500:
        return NetworkError(detail)
    return ModelError(detail)


class OpenAICompatibleProvider:
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
        headers = {"Content-Type": "application/json"}
        if self._config.api_key is not None:
            secret = self._config.api_key.get_secret_value()
            if self._config.api_key_header:
                headers[self._config.api_key_header] = secret
            else:
                headers["Authorization"] = f"Bearer {secret}"
        return headers

    def _payload(
        self,
        messages: list[ChatMessage],
        *,
        stream: bool,
        options: ChatOptions | None = None,
    ) -> dict:
        payload = {
            "model": self._config.model,
            "messages": [message.model_dump() for message in messages],
            "stream": stream,
        }
        if options is not None:
            payload.update(options.for_openai_payload())
        return payload

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

    def _client_kwargs(self) -> dict[str, object]:
        # Avoid broken system proxy settings (e.g. SOCKS without socksio).
        return {"timeout": 120.0, "trust_env": False}

    async def _complete_chat(
        self,
        messages: list[ChatMessage],
        *,
        options: ChatOptions | None = None,
    ) -> ChatCompletion:
        url = f"{self._base_url()}/chat/completions"
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
            content = data["choices"][0]["message"]["content"]
            if not content:
                raise ModelError("Empty completion content")
            usage_raw = data.get("usage") or {}
            return ChatCompletion(
                content=content,
                model=data.get("model", self._config.model),
                usage=TokenUsage(
                    prompt_tokens=usage_raw.get("prompt_tokens", 0),
                    completion_tokens=usage_raw.get("completion_tokens", 0),
                ),
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError(f"Malformed response: {response.text}") from exc

    async def _stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        options: ChatOptions | None = None,
    ) -> AsyncIterator[str]:
        url = f"{self._base_url()}/chat/completions"
        payload = self._payload(messages, stream=True, options=options)

        try:
            if self._client is not None:
                client = self._client
                response_cm = client.stream(
                    "POST",
                    url,
                    headers=self._headers(),
                    json=payload,
                )
            else:
                client = httpx.AsyncClient(**self._client_kwargs())
                response_cm = client.stream(
                    "POST",
                    url,
                    headers=self._headers(),
                    json=payload,
                )

            async with response_cm as response:
                if response.is_error:
                    body = await response.aread()
                    raise map_http_error(response.status_code, body.decode())

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content")
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue
                    if delta:
                        yield delta

            if self._client is None:
                await client.aclose()
        except httpx.RequestError as exc:
            raise NetworkError(str(exc)) from exc
