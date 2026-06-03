import json
from collections.abc import AsyncIterator

import httpx

from llm_providers.base import (
    ChatCompletion,
    ChatMessage,
    ChatOptions,
    ModelError,
    NetworkError,
    TokenUsage,
)
from llm_providers.config import ProviderConfig
from llm_providers.openai_compatible import map_http_error

DEFAULT_BASE_URL = "http://127.0.0.1:11434"


class OllamaProvider:
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
            headers["Authorization"] = f"Bearer {self._config.api_key.get_secret_value()}"
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
            payload.update(options.for_ollama_payload())
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
        url = f"{self._base_url()}/api/chat"
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
            content = data["message"]["content"]
            if not content:
                raise ModelError("Empty completion content")
            return ChatCompletion(
                content=content,
                model=data.get("model", self._config.model),
                usage=TokenUsage(
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
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
        url = f"{self._base_url()}/api/chat"
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
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("message", {}).get("content")
                    except json.JSONDecodeError:
                        continue
                    if delta:
                        yield delta

            if self._client is None:
                await client.aclose()
        except httpx.RequestError as exc:
            raise NetworkError(str(exc)) from exc
