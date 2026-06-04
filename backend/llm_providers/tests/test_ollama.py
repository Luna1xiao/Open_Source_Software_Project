import httpx
import pytest

from llm_providers.base import ChatMessage
from llm_providers.config import ProviderConfig, ProviderKind
from llm_providers.ollama import OllamaProvider


def _provider(handler) -> OllamaProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    return OllamaProvider(
        ProviderConfig(
            name="ollama",
            kind=ProviderKind.OLLAMA,
            model="llama3",
            base_url="http://testserver",
        ),
        client=client,
    )


@pytest.mark.asyncio
async def test_complete_chat_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        body = request.read().decode()
        assert '"stream": false' in body or '"stream":false' in body
        return httpx.Response(
            200,
            json={
                "model": "llama3",
                "message": {"role": "assistant", "content": "hello from ollama"},
                "done": True,
                "prompt_eval_count": 4,
                "eval_count": 2,
            },
        )

    provider = _provider(handler)
    result = await provider.chat([ChatMessage(role="user", content="hi")])
    assert result.content == "hello from ollama"
    assert result.usage.prompt_tokens == 4
    assert result.usage.completion_tokens == 2


@pytest.mark.asyncio
async def test_stream_chat_success():
    stream_body = "\n".join(
        [
            '{"message":{"content":"hel"}}',
            '{"message":{"content":"lo"}}',
            '{"message":{"content":""},"done":true}',
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        assert '"stream": true' in body or '"stream":true' in body
        return httpx.Response(200, text=stream_body)

    provider = _provider(handler)
    stream = await provider.chat([ChatMessage(role="user", content="hi")], stream=True)
    chunks = [chunk async for chunk in stream]
    assert chunks == ["hel", "lo"]
