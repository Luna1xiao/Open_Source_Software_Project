import httpx
import pytest
from pydantic import SecretStr

from llm_providers.base import AuthError, ChatMessage, ModelError, NetworkError, RateLimitError
from llm_providers.config import ProviderConfig, ProviderKind
from llm_providers.openai_compatible import OpenAICompatibleProvider


def _provider(handler) -> OpenAICompatibleProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    return OpenAICompatibleProvider(
        ProviderConfig(
            name="mock",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="gpt-test",
            base_url="http://testserver/v1",
            api_key=SecretStr("test-key"),
        ),
        client=client,
    )


@pytest.mark.asyncio
async def test_complete_chat_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = request.read().decode()
        assert '"stream": false' in body or '"stream":false' in body
        return httpx.Response(
            200,
            json={
                "model": "gpt-test",
                "choices": [{"message": {"role": "assistant", "content": "hello"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1},
            },
        )

    provider = _provider(handler)
    result = await provider.chat([ChatMessage(role="user", content="hi")])
    assert result.content == "hello"
    assert result.usage.prompt_tokens == 3
    assert result.usage.completion_tokens == 1


@pytest.mark.asyncio
async def test_complete_chat_with_api_key_header():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["api-key"] == "test-key"
        assert "authorization" not in request.headers
        return httpx.Response(
            200,
            json={
                "model": "mimo-test",
                "choices": [{"message": {"role": "assistant", "content": "mimo"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            },
        )

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            name="mimo",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="mimo-test",
            base_url="http://testserver/v1",
            api_key=SecretStr("test-key"),
            api_key_header="api-key",
        ),
        client=client,
    )
    result = await provider.chat([ChatMessage(role="user", content="hi")])
    assert result.content == "mimo"


@pytest.mark.asyncio
async def test_complete_chat_with_options():
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        assert '"temperature": 0.5' in body or '"temperature":0.5' in body
        assert '"max_completion_tokens": 128' in body or '"max_completion_tokens":128' in body
        return httpx.Response(
            200,
            json={
                "model": "gpt-test",
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            },
        )

    provider = _provider(handler)
    from llm_providers.base import ChatOptions

    result = await provider.chat(
        [ChatMessage(role="user", content="hi")],
        options=ChatOptions(temperature=0.5, max_completion_tokens=128),
    )
    assert result.content == "ok"


@pytest.mark.asyncio
async def test_stream_chat_success():
    stream_body = "\n".join(
        [
            'data: {"choices":[{"delta":{"content":"hel"}}]}',
            'data: {"choices":[{"delta":{"content":"lo"}}]}',
            "data: [DONE]",
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


@pytest.mark.parametrize(
    ("status_code", "error_type"),
    [
        (401, AuthError),
        (429, RateLimitError),
        (404, ModelError),
        (500, NetworkError),
    ],
)
@pytest.mark.asyncio
async def test_http_error_mapping(status_code, error_type):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="failure")

    provider = _provider(handler)
    with pytest.raises(error_type):
        await provider.chat([ChatMessage(role="user", content="hi")])
