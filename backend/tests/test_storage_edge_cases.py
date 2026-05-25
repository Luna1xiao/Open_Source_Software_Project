import sqlite3

from app.schemas.agent import SummaryResult
from app.schemas.entry import Entry
from app.schemas.feed import Feed
from db import (
    append_agent_step,
    finish_agent_run,
    get_article_content,
    get_latest_agent_result,
    init_db,
    query_usage,
    record_usage,
    save_agent_result,
    save_article,
    save_article_content,
    save_feed,
    search_articles,
    start_agent_run,
    storage_session,
    update_feed_sync_metadata,
)


def test_get_article_content_returns_none_for_missing_article(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    assert get_article_content("missing", db_path) is None


def test_update_feed_sync_metadata_returns_false_for_missing_feed(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    assert (
        update_feed_sync_metadata(
            feed_id="missing",
            last_fetched_at="2026-05-25T12:00:00Z",
            etag=None,
            last_modified=None,
            status="failure",
            db_path=db_path,
        )
        is False
    )


def test_latest_agent_result_ignores_failed_runs(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)

    save_agent_result(
        SummaryResult(
            entry_id="article-1",
            summary_text="Failed summary",
            status="failure",
            provider="mock",
            model="mock-model",
        ),
        db_path,
    )

    assert get_latest_agent_result("article-1", "summary", db_path) is None


def test_latest_agent_result_can_filter_translation_by_target_lang(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)

    zh_run = start_agent_run(
        article_id="article-1",
        agent_type="translation",
        provider="mock",
        model="mock-model",
        target_lang="zh-CN",
        db_path=db_path,
    )
    finish_agent_run(zh_run, "success", output_text="<p>你好</p>", db_path=db_path)
    en_run = start_agent_run(
        article_id="article-1",
        agent_type="translation",
        provider="mock",
        model="mock-model",
        target_lang="en-US",
        db_path=db_path,
    )
    finish_agent_run(en_run, "success", output_text="<p>Hello</p>", db_path=db_path)

    latest_zh = get_latest_agent_result(
        "article-1",
        "translation",
        db_path,
        target_lang="zh-CN",
    )

    assert latest_zh is not None
    assert latest_zh["id"] == zh_run
    assert latest_zh["output_text"] == "<p>你好</p>"


def test_agent_steps_are_ordered_by_append_sequence(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(_article(), db_path)
    run_id = start_agent_run("article-1", "summary", "mock", "mock-model", db_path)

    append_agent_step(run_id, "load", "success", db_path=db_path)
    append_agent_step(run_id, "summarize", "success", db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT step_index, name FROM agent_steps WHERE run_id = ? ORDER BY step_index",
            (run_id,),
        ).fetchall()

    assert rows == [(0, "load"), (1, "summarize")]


def test_query_usage_filters_by_date_range_model_and_agent(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    record_usage("2026-05-24", "mock", "small", "summary", 1, 1, db_path)
    record_usage("2026-05-25", "mock", "large", "summary", 10, 5, db_path)
    record_usage("2026-05-26", "mock", "large", "translation", 20, 10, db_path)

    buckets = query_usage(
        start_day="2026-05-25",
        end_day="2026-05-26",
        provider="mock",
        model="large",
        agent="summary",
        db_path=db_path,
    )

    assert [bucket.day for bucket in buckets] == ["2026-05-25"]
    assert buckets[0].prompt_tokens == 10
    assert buckets[0].completion_tokens == 5


def test_fts_search_indexes_title_summary_and_plain_text(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)
    save_feed(_feed(), db_path)
    save_article(
        _article(title="Orbit notes", summary="A short note about storage"),
        db_path,
    )
    save_article_content(
        article_id="article-1",
        raw_html="<p>Cleaner content</p>",
        cleaned_html="<p>Cleaner content</p>",
        cleaned_markdown="Cleaner content",
        plain_text="Markdown body is searchable",
        db_path=db_path,
    )

    assert [article.id for article in search_articles("Orbit", db_path=db_path)] == ["article-1"]
    assert [article.id for article in search_articles("storage", db_path=db_path)] == [
        "article-1"
    ]
    assert [article.id for article in search_articles("Markdown", db_path=db_path)] == [
        "article-1"
    ]


def test_storage_session_rolls_back_on_error(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    try:
        with storage_session(db_path) as session:
            assert session.conn is not None
            session.conn.execute(
                """
                INSERT INTO feeds (id, title, site_url, feed_url, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "feed-rollback",
                    "Rollback Feed",
                    "",
                    "https://example.com/rollback.xml",
                    "idle",
                ),
            )
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM feeds WHERE id = 'feed-rollback'",
        ).fetchone()[0]

    assert count == 0


def _feed() -> Feed:
    return Feed(
        id="feed-1",
        title="Mercury Blog",
        site_url="https://example.com",
        feed_url="https://example.com/feed.xml",
        unread_count=0,
        status="idle",
    )


def _article(
    title: str = "First article",
    summary: str = "Short summary",
) -> Entry:
    return Entry(
        id="article-1",
        feed_id="feed-1",
        title=title,
        summary=summary,
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
