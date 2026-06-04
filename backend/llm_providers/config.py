from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr, field_serializer

PROVIDERS_FILENAME = "providers.json"


class ProviderKind(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class ProviderConfig(BaseModel):
    name: str
    kind: ProviderKind
    model: str
    base_url: str | None = None
    api_key: SecretStr | None = None
    api_key_header: str | None = None
    is_default: bool = False

    @field_serializer("api_key", when_used="json-unless-none")
    def serialize_api_key(self, api_key: SecretStr | None) -> str | None:
        if api_key is None:
            return None
        return api_key.get_secret_value()


class ProviderSummary(BaseModel):
    name: str
    kind: ProviderKind
    model: str
    base_url: str | None = None
    api_key_header: str | None = None
    is_default: bool = False
    has_api_key: bool = False


def to_provider_summary(config: ProviderConfig) -> ProviderSummary:
    return ProviderSummary(
        name=config.name,
        kind=config.kind,
        model=config.model,
        base_url=config.base_url,
        api_key_header=config.api_key_header,
        is_default=config.is_default,
        has_api_key=config.api_key is not None,
    )


class ProvidersFile(BaseModel):
    providers: list[ProviderConfig] = Field(default_factory=list)


def providers_path(data_dir: Path) -> Path:
    return data_dir / PROVIDERS_FILENAME


def load_providers_file(path: Path) -> ProvidersFile:
    if not path.exists():
        return ProvidersFile()
    return ProvidersFile.model_validate_json(path.read_text(encoding="utf-8"))


def save_providers_file(path: Path, data: ProvidersFile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data.model_dump_json(indent=2), encoding="utf-8")
