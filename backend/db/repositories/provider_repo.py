import json
from pathlib import Path
from typing import Any

from db.connection import connection


def save_provider_settings(
    provider: str,
    enabled: bool,
    db_path: Path | str | None = None,
    base_url: str | None = None,
    default_model: str | None = None,
    api_key_ref: str | None = None,
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upsert LLM provider settings; stores api_key_ref, not raw API keys."""
    payload = settings or {}
    with connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO provider_settings (
                    provider,
                    enabled,
                    base_url,
                    default_model,
                    api_key_ref,
                    settings_json,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(provider) DO UPDATE SET
                    enabled = excluded.enabled,
                    base_url = excluded.base_url,
                    default_model = excluded.default_model,
                    api_key_ref = excluded.api_key_ref,
                    settings_json = excluded.settings_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    provider,
                    int(enabled),
                    base_url,
                    default_model,
                    api_key_ref,
                    json.dumps(payload),
                ),
            )
    return {
        "provider": provider,
        "enabled": enabled,
        "base_url": base_url,
        "default_model": default_model,
        "api_key_ref": api_key_ref,
        "settings": payload,
    }


def get_provider_settings(
    provider: str,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """Return settings for one LLM provider."""
    with connection(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM provider_settings WHERE provider = ?",
            (provider,),
        ).fetchone()
    return _row_to_provider_settings(row) if row is not None else None


def list_provider_settings(db_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Return all configured LLM providers ordered by name."""
    with connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM provider_settings ORDER BY provider ASC",
        ).fetchall()
    return [_row_to_provider_settings(row) for row in rows]


def delete_provider_settings(provider: str, db_path: Path | str | None = None) -> bool:
    """Delete one provider settings record."""
    with connection(db_path) as conn:
        with conn:
            cursor = conn.execute(
                "DELETE FROM provider_settings WHERE provider = ?",
                (provider,),
            )
    return cursor.rowcount > 0


def _row_to_provider_settings(row) -> dict[str, Any]:
    return {
        "provider": row["provider"],
        "enabled": bool(row["enabled"]),
        "base_url": row["base_url"],
        "default_model": row["default_model"],
        "api_key_ref": row["api_key_ref"],
        "settings": json.loads(row["settings_json"]),
    }
