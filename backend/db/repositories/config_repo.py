import json
from pathlib import Path
from typing import Any

from db.connection import connection


def set_app_config(
    key: str,
    value: dict[str, Any],
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    """Set one JSON app configuration value."""
    with connection(db_path) as conn:
        with conn:
            conn.execute(
                """
                INSERT INTO app_config (key, value_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value)),
            )
    return value


def get_app_config(
    key: str,
    default: dict[str, Any] | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any] | None:
    """Return one JSON app configuration value or default."""
    with connection(db_path) as conn:
        row = conn.execute(
            "SELECT value_json FROM app_config WHERE key = ?",
            (key,),
        ).fetchone()
    return json.loads(row["value_json"]) if row is not None else default


def delete_app_config(key: str, db_path: Path | str | None = None) -> bool:
    """Delete one app configuration value."""
    with connection(db_path) as conn:
        with conn:
            cursor = conn.execute("DELETE FROM app_config WHERE key = ?", (key,))
    return cursor.rowcount > 0
