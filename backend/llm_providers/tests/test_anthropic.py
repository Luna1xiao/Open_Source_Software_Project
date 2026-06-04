import json

import httpx
import pytest
from pydantic import SecretStr

from llm_providers.anthropic import AnthropicProvider
from llm_providers.base import ChatMessage, ChatOptions, NetworkError
from llm_providers.config import ProviderConfig, ProviderKind


def _provider(handler) -> AnthropicProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    return AnthropicProvider(
        ProviderConfig(
            name="anthropic",
            kind=ProviderKind.ANTHROPIC,
            model="claude-test",
            base_url="http://testserver/v1",
            api_key=SecretStr("test-key"),
        ),
        client=client,
    )


@pytest.mark.asyncio
async def test_complete_chat_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        body = json.loads(request.read().decode())
        assert body["model"] == "claude-test"
        assert body["stream"] is False
        assert body["max_tokens"] == 64
        assert body["system"] == "Keep it short."
        assert body["messages"] == [{"role": "user", "content": "hi"}]
        return httpx.Response(
            200,
            json={
                "model": "claude-test",
                "content": [{"type": "text", "text": "hello"}],
                "usage": {"input_tokens": 3, "output_tokens": 1},
            },
        )

    provider = _provider(handler)
    result = await provider.chat(
        [
            ChatMessage(role="system", content="Keep it short."),
            ChatMessage(role="user", content="hi"),
        ],
        options=ChatOptions(max_completion_tokens=64),
    )
    assert result.content == "hello"
    assert result.usage.prompt_tokens == 3
    assert result.usage.completion_tokens == 1


@pytest.mark.asyncio
async def test_complete_chat_uses_custom_api_key_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        assert "x-api-key" not in request.headers
        return httpx.Response(
            200,
            json={
                "model": "claude-test",
                "content": [{"type": "text", "text": "ok"}],
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    provider = AnthropicProvider(
        ProviderConfig(
            name="anthropic-proxy",
            kind=ProviderKind.ANTHROPIC,
            model="claude-test",
            base_url="http://testserver/v1",
            api_key=SecretStr("Bearer test-key"),
            api_key_header="authorization",
        ),
        client=client,
    )

    result = await provider.chat([ChatMessage(role="user", content="hi")])
    assert result.content == "ok"


@pytest.mark.asyncio
async def test_stream_chat_success():
    stream_body = "\n".join(
        [
            'event: message_start\ndata: {"type":"message_start"}',
            (
                'event: content_block_delta\n'
                'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"hel"}}'
            ),
            (
                'event: content_block_delta\n'
                'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"lo"}}'
            ),
            'event: message_stop\ndata: {"type":"message_stop"}',
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read().decode())
        assert body["stream"] is True
        return httpx.Response(200, text=stream_body)

    provider = _provider(handler)
    stream = await provider.chat([ChatMessage(role="user", content="hi")], stream=True)
    chunks = [chunk async for chunk in stream]
    assert chunks == ["hel", "lo"]


@pytest.mark.asyncio
async def test_stream_chat_error_event_raises():
    stream_body = (
        'event: error\n'
        'data: {"type":"error","error":{"type":"overloaded_error","message":"overloaded"}}'
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=stream_body)

    provider = _provider(handler)
    stream = await provider.chat([ChatMessage(role="user", content="hi")], stream=True)
    with pytest.raises(NetworkError):
        _ = [chunk async for chunk in stream]
