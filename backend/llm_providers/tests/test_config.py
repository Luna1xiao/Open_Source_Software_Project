from pydantic import SecretStr

from llm_providers.config import (
    ProviderConfig,
    ProviderKind,
    ProvidersFile,
    load_providers_file,
    save_providers_file,
)


def test_save_providers_preserves_api_key(tmp_path):
    path = tmp_path / "providers.json"
    config = ProviderConfig(
        name="mimo",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        model="mimo-v2.5-pro",
        base_url="https://token-plan-cn.xiaomimimo.com/v1",
        api_key=SecretStr("tp-real-secret-key"),
        api_key_header="api-key",
        is_default=True,
    )

    save_providers_file(path, ProvidersFile(providers=[config]))

    raw = path.read_text(encoding="utf-8")
    assert "tp-real-secret-key" in raw
    assert "**********" not in raw

    loaded = load_providers_file(path)
    assert loaded.providers[0].api_key is not None
    assert loaded.providers[0].api_key.get_secret_value() == "tp-real-secret-key"
