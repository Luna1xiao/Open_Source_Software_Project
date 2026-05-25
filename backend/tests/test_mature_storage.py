import sqlite3

from app.schemas.agent import SummaryResult
from app.schemas.entry import Entry
from app.schemas.feed import Feed
from app.schemas.tag import Tag
from db import (
    append_agent_step,
    backup_database,
    delete_feed,
    finish_agent_run,
    get_article,
    get_latest_agent_result,
    init_db,
    list_articles,
    query_usage,
    record_usage,
    save_agent_result,
    save_article,
    save_article_content,
    save_feed,
    save_tag,
    set_article_tags,
    start_agent_run,
    storage_session,
)


def test_tags_can_be_assigned_and_used_to_filter_articles(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    article = _article()
    save_article(article, db_path)
    save_tag(Tag(id="tag-ai", name="AI", aliases=["llm"], usage_count=0, unread_count=0), db_path)

    set_article_tags("article-1", ["tag-ai"], db_path)

    tagged_article = list_articles(tag_id="tag-ai", db_path=db_path)[0]
    assert tagged_article.id == "article-1"
    assert tagged_article.tag_ids == ["tag-ai"]


def test_agent_run_steps_and_latest_result_are_persisted(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)

    run_id = start_agent_run(
        article_id="article-1",
        agent_type="summary",
        provider="mock",
        model="mock-model",
        db_path=db_path,
    )
    append_agent_step(run_id, "load_article", "success", output_json={"ok": True}, db_path=db_path)
    finish_agent_run(
        run_id,
        "success",
        output_text="Short summary",
        prompt_tokens=10,
        completion_tokens=5,
        db_path=db_path,
    )

    latest = get_latest_agent_result("article-1", "summary", db_path)

    assert latest is not None
    assert latest["id"] == run_id
    assert latest["output_text"] == "Short summary"
    assert latest["total_tokens"] == 15


def test_save_agent_result_updates_article_projection(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)

    save_agent_result(
        SummaryResult(
            entry_id="article-1",
            summary_text="Agent summary",
            status="success",
            provider="mock",
            model="mock-model",
        ),
        db_path,
    )

    article = get_article("article-1", db_path)
    assert article is not None
    assert article.summary_text == "Agent summary"


def test_usage_buckets_are_aggregated(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    record_usage("2026-05-25", "mock", "mock-model", "summary", 10, 5, db_path)
    record_usage("2026-05-25", "mock", "mock-model", "summary", 7, 3, db_path, failed=True)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM usage_buckets").fetchone()

    assert row[4] == 17
    assert row[5] == 8
    assert row[6] == 2
    assert row[7] == 1

    buckets = query_usage(provider="mock", agent="summary", db_path=db_path)
    assert len(buckets) == 1
    assert buckets[0].prompt_tokens == 17
    assert buckets[0].completion_tokens == 8
    assert buckets[0].requests == 2
    assert buckets[0].failures == 1


def test_delete_feed_cascades_articles_content_tags_and_agent_runs(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)
    save_article_content(
        article_id="article-1",
        raw_html="<p>Hello</p>",
        cleaned_html="<p>Hello</p>",
        cleaned_markdown="Hello",
        plain_text="Hello",
        db_path=db_path,
    )
    save_tag(Tag(id="tag-ai", name="AI", aliases=[], usage_count=0, unread_count=0), db_path)
    set_article_tags("article-1", ["tag-ai"], db_path)
    save_agent_result(
        SummaryResult(
            entry_id="article-1",
            summary_text="Agent summary",
            status="success",
            provider="mock",
            model="mock-model",
        ),
        db_path,
    )

    assert delete_feed("feed-1", db_path) is True

    with sqlite3.connect(db_path) as conn:
        article_count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        content_count = conn.execute("SELECT COUNT(*) FROM article_content").fetchone()[0]
        agent_run_count = conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()[0]
        article_tag_count = conn.execute("SELECT COUNT(*) FROM article_tags").fetchone()[0]

    assert article_count == 0
    assert content_count == 0
    assert agent_run_count == 0
    assert article_tag_count == 0


def test_agent_run_status_rejects_invalid_values(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)

    with sqlite3.connect(db_path) as conn:
        try:
            conn.execute(
                """
                INSERT INTO agent_runs (id, article_id, agent_type, status)
                VALUES ('bad-run', 'article-1', 'summary', 'done')
                """
            )
        except sqlite3.IntegrityError as exc:
            assert "invalid agent_runs.status" in str(exc)
        else:
            raise AssertionError("invalid agent_runs.status was accepted")


def test_backup_database_copies_current_database(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    backup_path = tmp_path / "backup.db"
    init_db(db_path)
    save_feed(_feed(), db_path)

    backup_database(backup_path, db_path)

    with sqlite3.connect(backup_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0] == 1


def test_storage_session_shares_one_connection(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    with storage_session(db_path) as session:
        assert session.conn is not None
        session.conn.execute(
            """
            INSERT INTO feeds (id, title, site_url, feed_url, status)
            VALUES ('feed-session', 'Session Feed', '', 'https://example.com/session.xml', 'idle')
            """
        )

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM feeds").fetchone()[0] == 1


def _feed() -> Feed:
    return Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )


def _article() -> Entry:
    return Entry(
        id="article-1",
        feed_id="feed-1",
        title="First article",
        summary="Short summary",
        author="Mercury Team",
        url="https://example.com/articles/1",
        published_at="2026-05-25T08:00:00Z",
        is_read=False,
        is_starred=False,
        tag_ids=[],
        reader_html="<p>Hello Mercury</p>",
        web_preview="",
        related_entry_ids=[],
        note="",
        summary_text="",
        translation_html=None,
        translation_status="idle",
    )
