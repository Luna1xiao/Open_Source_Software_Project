from pathlib import Path

from app.config import settings
from llm_providers.anthropic import AnthropicProvider
from llm_providers.base import LLMProvider, ModelError, ProviderNotFoundError
from llm_providers.config import (
    ProviderConfig,
    ProviderKind,
    ProvidersFile,
    ProviderSummary,
    load_providers_file,
    providers_path,
    save_providers_file,
    to_provider_summary,
)
from llm_providers.ollama import OllamaProvider
from llm_providers.openai_compatible import OpenAICompatibleProvider

_config_path: Path | None = None


def set_config_path(path: Path) -> None:
    """Override the providers file path (used in tests)."""
    global _config_path
    _config_path = path


def reset_config_path() -> None:
    global _config_path
    _config_path = None


def resolved_config_path() -> Path:
    if _config_path is not None:
        return _config_path
    return providers_path(settings.data_dir)


def load_providers_from_config() -> list[ProviderConfig]:
    return load_providers_file(resolved_config_path()).providers


def _write_providers(providers: list[ProviderConfig]) -> None:
    save_providers_file(resolved_config_path(), ProvidersFile(providers=providers))


def _build_provider(config: ProviderConfig) -> LLMProvider:
    if config.kind == ProviderKind.OPENAI_COMPATIBLE:
        return OpenAICompatibleProvider(config)
    if config.kind == ProviderKind.ANTHROPIC:
        return AnthropicProvider(config)
    if config.kind == ProviderKind.OLLAMA:
        return OllamaProvider(config)
    raise ModelError(f"Unknown provider kind: {config.kind}")


def _resolve_config_name(name: str | None) -> ProviderConfig:
    providers = load_providers_from_config()
    if not providers:
        raise ProviderNotFoundError("No providers configured")

    if name is None:
        defaults = [provider for provider in providers if provider.is_default]
        if len(defaults) == 1:
            return defaults[0]
        if len(defaults) > 1:
            raise ModelError("Multiple default providers configured")
        return providers[0]

    for provider in providers:
        if provider.name == name:
            return provider
    raise ProviderNotFoundError(f"Provider not found: {name}")


def get_provider(name: str | None = None) -> LLMProvider:
    config = _resolve_config_name(name)
    return _build_provider(config)


async def list_providers() -> list[ProviderConfig]:
    return load_providers_from_config()


async def list_provider_summaries() -> list[ProviderSummary]:
    return [to_provider_summary(provider) for provider in load_providers_from_config()]


async def add_provider(config: ProviderConfig) -> None:
    providers = load_providers_from_config()

    if any(existing.name == config.name for existing in providers):
        raise ModelError(f"Provider already exists: {config.name}")

    if config.is_default:
        providers = [
            existing.model_copy(update={"is_default": False}) for existing in providers
        ]

    providers.append(config)
    _write_providers(providers)


async def update_provider(config: ProviderConfig) -> None:
    providers = load_providers_from_config()
    if not any(existing.name == config.name for existing in providers):
        raise ProviderNotFoundError(f"Provider not found: {config.name}")

    if config.is_default:
        providers = [
            existing.model_copy(update={"is_default": False}) for existing in providers
        ]

    updated: list[ProviderConfig] = []
    for existing in providers:
        if existing.name == config.name:
            updated.append(config)
        else:
            updated.append(existing)

    _write_providers(updated)


async def remove_provider(name: str) -> None:
    providers = load_providers_from_config()
    filtered = [provider for provider in providers if provider.name != name]
    if len(filtered) == len(providers):
        raise ProviderNotFoundError(f"Provider not found: {name}")
    _write_providers(filtered)
