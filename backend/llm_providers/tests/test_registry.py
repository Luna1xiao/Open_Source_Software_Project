import pytest
from pydantic import SecretStr

from llm_providers.anthropic import AnthropicProvider
from llm_providers.base import ProviderNotFoundError
from llm_providers.config import ProviderConfig, ProviderKind, load_providers_file
from llm_providers.ollama import OllamaProvider
from llm_providers.openai_compatible import OpenAICompatibleProvider
from llm_providers.registry import (
    add_provider,
    get_provider,
    list_providers,
    reset_config_path,
    set_config_path,
)


@pytest.fixture
def providers_file(tmp_path):
    path = tmp_path / "providers.json"
    set_config_path(path)
    yield path
    reset_config_path()


@pytest.mark.asyncio
async def test_add_and_list_providers(providers_file):
    await add_provider(
        ProviderConfig(
            name="openai",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="gpt-4o-mini",
            base_url="https://api.openai.com/v1",
            is_default=True,
        )
    )
    await add_provider(
        ProviderConfig(
            name="ollama",
            kind=ProviderKind.OLLAMA,
            model="llama3",
            base_url="http://127.0.0.1:11434",
        )
    )

    providers = await list_providers()
    assert [provider.name for provider in providers] == ["openai", "ollama"]

    stored = load_providers_file(providers_file)
    assert stored.providers[0].is_default is True
    assert stored.providers[1].is_default is False


@pytest.mark.asyncio
async def test_add_provider_replaces_existing_default(providers_file):
    await add_provider(
        ProviderConfig(
            name="openai",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="gpt-4o-mini",
            is_default=True,
        )
    )
    await add_provider(
        ProviderConfig(
            name="ollama",
            kind=ProviderKind.OLLAMA,
            model="llama3",
            is_default=True,
        )
    )

    providers = await list_providers()
    assert providers[0].is_default is False
    assert providers[1].is_default is True


def test_get_provider_by_name(providers_file):
    providers_file.write_text(
        """
        {
          "providers": [
            {
              "name": "openai",
              "kind": "openai_compatible",
              "model": "gpt-4o-mini",
              "is_default": true
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    provider = get_provider("openai")
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.name == "openai"
    assert provider.model == "gpt-4o-mini"


def test_get_default_provider(providers_file):
    providers_file.write_text(
        """
        {
          "providers": [
            {
              "name": "ollama",
              "kind": "ollama",
              "model": "llama3",
              "is_default": true
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    provider = get_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider.name == "ollama"


def test_get_anthropic_provider(providers_file):
    providers_file.write_text(
        """
        {
          "providers": [
            {
              "name": "claude",
              "kind": "anthropic",
              "model": "claude-sonnet-4-5",
              "is_default": true
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    provider = get_provider("claude")
    assert isinstance(provider, AnthropicProvider)
    assert provider.name == "claude"


def test_get_provider_missing_raises(providers_file):
    with pytest.raises(ProviderNotFoundError):
        get_provider("missing")


@pytest.mark.asyncio
async def test_add_provider_persists_api_key(providers_file):
    await add_provider(
        ProviderConfig(
            name="mimo",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="mimo-v2.5-pro",
            base_url="https://token-plan-cn.xiaomimimo.com/v1",
            api_key=SecretStr("tp-roundtrip-secret"),
            api_key_header="api-key",
            is_default=True,
        )
    )

    raw = providers_file.read_text(encoding="utf-8")
    assert "tp-roundtrip-secret" in raw
    assert "**********" not in raw

    reloaded = load_providers_file(providers_file)
    assert reloaded.providers[0].api_key.get_secret_value() == "tp-roundtrip-secret"


@pytest.mark.asyncio
async def test_list_provider_summaries_masks_api_key(providers_file):
    await add_provider(
        ProviderConfig(
            name="mimo",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="mimo-v2.5-pro",
            api_key=SecretStr("tp-secret"),
            is_default=True,
        )
    )

    from llm_providers.registry import list_provider_summaries

    summaries = await list_provider_summaries()
    assert len(summaries) == 1
    assert summaries[0].has_api_key is True
    assert "api_key" not in summaries[0].model_dump()


@pytest.mark.asyncio
async def test_update_and_remove_provider(providers_file):
    await add_provider(
        ProviderConfig(
            name="openai",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="gpt-4o-mini",
            is_default=True,
        )
    )

    from llm_providers.registry import remove_provider, update_provider

    await update_provider(
        ProviderConfig(
            name="openai",
            kind=ProviderKind.OPENAI_COMPATIBLE,
            model="gpt-4.1-mini",
            is_default=True,
        )
    )
    providers = await list_providers()
    assert providers[0].model == "gpt-4.1-mini"

    await remove_provider("openai")
    assert await list_providers() == []
