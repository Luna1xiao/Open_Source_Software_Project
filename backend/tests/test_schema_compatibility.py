import sqlite3

from db import init_db


def test_init_db_upgrades_database_with_only_initial_migration(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE feeds (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              site_url TEXT NOT NULL DEFAULT '',
              feed_url TEXT NOT NULL UNIQUE,
              description TEXT NOT NULL DEFAULT '',
              language TEXT,
              last_fetched_at TEXT,
              etag TEXT,
              last_modified TEXT,
              status TEXT NOT NULL DEFAULT 'idle',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE articles (
              id TEXT PRIMARY KEY,
              feed_id TEXT NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
              title TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT '',
              author TEXT NOT NULL DEFAULT '',
              url TEXT NOT NULL,
              guid TEXT,
              published_at TEXT,
              fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              is_read INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0, 1)),
              is_starred INTEGER NOT NULL DEFAULT 0 CHECK (is_starred IN (0, 1)),
              note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(feed_id, guid),
              UNIQUE(feed_id, url)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE article_content (
              article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
              raw_html TEXT NOT NULL DEFAULT '',
              cleaned_html TEXT NOT NULL DEFAULT '',
              cleaned_markdown TEXT NOT NULL DEFAULT '',
              plain_text TEXT NOT NULL DEFAULT '',
              content_hash TEXT,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE agent_runs (
              id TEXT PRIMARY KEY,
              article_id TEXT REFERENCES articles(id) ON DELETE CASCADE,
              agent_type TEXT NOT NULL CHECK (agent_type IN ('summary', 'translation', 'tag')),
              status TEXT NOT NULL,
              provider TEXT NOT NULL DEFAULT '',
              model TEXT NOT NULL DEFAULT '',
              input_hash TEXT,
              target_lang TEXT,
              output_text TEXT,
              output_json TEXT,
              error_message TEXT,
              prompt_tokens INTEGER NOT NULL DEFAULT 0,
              completion_tokens INTEGER NOT NULL DEFAULT 0,
              total_tokens INTEGER NOT NULL DEFAULT 0,
              started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              finished_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE agent_steps (
              id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
              step_index INTEGER NOT NULL,
              name TEXT NOT NULL,
              status TEXT NOT NULL,
              input_json TEXT,
              output_json TEXT,
              error_message TEXT,
              started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              finished_at TEXT,
              UNIQUE(run_id, step_index)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE provider_settings (
              provider TEXT PRIMARY KEY,
              enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
              base_url TEXT,
              default_model TEXT,
              api_key_ref TEXT,
              settings_json TEXT NOT NULL DEFAULT '{}',
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE app_config (
              key TEXT PRIMARY KEY,
              value_json TEXT NOT NULL,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("INSERT INTO schema_migrations(version) VALUES ('001_initial.sql')")

    init_db(db_path)
    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert {
        "001_initial.sql",
        "002_mature_storage.sql",
        "003_agent_status_constraints.sql",
        "004_article_fts.sql",
    }.issubset(applied)
    assert {"tags", "usage_buckets", "article_search", "article_fts"}.issubset(tables)
