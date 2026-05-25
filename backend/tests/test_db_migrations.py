import sqlite3

from db import init_db


def test_init_db_creates_core_tables(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"

    init_db(db_path)
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        }
        applied_versions = {
            row[0] for row in conn.execute("SELECT version FROM schema_migrations")
        }

    assert {
        "schema_migrations",
        "feeds",
        "articles",
        "article_content",
        "agent_runs",
        "agent_steps",
        "provider_settings",
        "app_config",
        "article_fts",
    }.issubset(table_names)
    assert applied_versions == {
        "001_initial.sql",
        "002_mature_storage.sql",
        "003_agent_status_constraints.sql",
        "004_article_fts.sql",
    }
