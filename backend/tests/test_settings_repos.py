from db import (
    delete_app_config,
    delete_provider_settings,
    get_app_config,
    get_provider_settings,
    init_db,
    list_provider_settings,
    save_provider_settings,
    set_app_config,
)


def test_provider_settings_crud(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    saved = save_provider_settings(
        provider="mock",
        enabled=True,
        base_url="https://llm.example.com",
        default_model="mock-large",
        api_key_ref="secret://mock",
        settings={"temperature": 0.2},
        db_path=db_path,
    )

    assert saved["api_key_ref"] == "secret://mock"
    assert get_provider_settings("mock", db_path) == saved
    assert list_provider_settings(db_path) == [saved]
    assert delete_provider_settings("mock", db_path) is True
    assert get_provider_settings("mock", db_path) is None


def test_provider_settings_update_replaces_previous_values(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    save_provider_settings(
        provider="mock",
        enabled=True,
        default_model="old-model",
        api_key_ref="secret://old",
        settings={"temperature": 0.1},
        db_path=db_path,
    )
    updated = save_provider_settings(
        provider="mock",
        enabled=False,
        default_model="new-model",
        api_key_ref="secret://new",
        settings={"temperature": 0.5},
        db_path=db_path,
    )

    assert get_provider_settings("mock", db_path) == updated


def test_app_config_crud(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    set_app_config("ui.locale", {"value": "zh-CN"}, db_path)

    assert get_app_config("ui.locale", db_path=db_path) == {"value": "zh-CN"}
    assert get_app_config("missing", default={"value": "en-US"}, db_path=db_path) == {
        "value": "en-US"
    }
    assert delete_app_config("ui.locale", db_path) is True
    assert get_app_config("ui.locale", db_path=db_path) is None


def test_app_config_update_replaces_json_value(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    set_app_config("sync", {"interval_minutes": 15}, db_path)
    set_app_config("sync", {"interval_minutes": 30, "enabled": True}, db_path)

    assert get_app_config("sync", db_path=db_path) == {
        "interval_minutes": 30,
        "enabled": True,
    }
