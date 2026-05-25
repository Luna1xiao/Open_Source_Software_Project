import sqlite3
from pathlib import Path

from db.connection import connection

SCHEMA_DIR = Path(__file__).with_name("schema")


def init_db(db_path: Path | str | None = None) -> None:
    with connection(db_path) as conn:
        run_migrations(conn)


def run_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied_versions = {
        row["version"] for row in conn.execute("SELECT version FROM schema_migrations")
    }

    for migration_path in sorted(SCHEMA_DIR.glob("*.sql")):
        version = migration_path.name
        if version in applied_versions:
            continue

        sql = migration_path.read_text(encoding="utf-8")
        with conn:
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
