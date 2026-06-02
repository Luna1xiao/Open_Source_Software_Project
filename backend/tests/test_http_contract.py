from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.schemas.entry import Entry
from app.schemas.feed import Feed
from app.schemas.tag import Tag
from db import (
    get_article,
    init_db,
    save_article,
    save_article_content,
    save_feed,
    save_tag,
    set_article_tags,
)


@pytest.fixture
def api_db(tmp_path, monkeypatch) -> Iterator[str]:
    db_path = tmp_path / "mercury-http.db"
    monkeypatch.setattr(settings, "db_path", db_path)
    init_db(db_path)

    save_feed(
        Feed(
            id="feed-1",
            title="Mercury Blog",
            site_url="https://example.com",
            feed_url="https://example.com/feed.xml",
            unread_count=0,
            status="idle",
        ),
        db_path,
    )
    save_tag(
        Tag(id="tag-ai", name="AI", aliases=["llm"], usage_count=0, unread_count=0),
        db_path,
    )

    save_article(_article("article-1", reader_html="<p>Hello Mercury</p>"), db_path)
    save_article(_article("article-empty", reader_html=""), db_path)
    save_article_content(
        article_id="article-1",
        raw_html="<main><p>Hello Mercury</p></main>",
        cleaned_html="<p>Hello Mercury</p>",
        cleaned_markdown="Hello Mercury",
        plain_text="Hello Mercury",
        db_path=db_path,
    )
    set_article_tags("article-1", ["tag-ai"], db_path)

    yield str(db_path)


@pytest.fixture
def api_client(api_db: str) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def test_get_feeds_tags_and_entries_return_contract_shapes(api_client: TestClient) -> None:
    feeds = api_client.get("/feeds")
    tags = api_client.get("/tags")
    entries = api_client.get("/entries")
    entry = api_client.get("/entries/article-1")

    assert feeds.status_code == 200
    assert feeds.json() == [
        {
            "id": "feed-1",
            "title": "Mercury Blog",
            "site_url": "https://example.com",
            "feed_url": "https://example.com/feed.xml",
            "unread_count": 2,
            "status": "idle",
        }
    ]

    assert tags.status_code == 200
    assert tags.json() == [
        {
            "id": "tag-ai",
            "name": "AI",
            "aliases": ["llm"],
            "usage_count": 1,
            "unread_count": 1,
        }
    ]

    assert entries.status_code == 200
    assert [item["id"] for item in entries.json()] == ["article-1", "article-empty"]

    assert entry.status_code == 200
    assert entry.json()["summary_text"] == ""
    assert entry.json()["tag_ids"] == ["tag-ai"]


def test_get_entries_supports_keyword_and_feed_filters(api_client: TestClient) -> None:
    response = api_client.get("/entries", params={"keyword": "Mercury", "feed_id": "feed-1"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["article-1"]


def test_entry_mutations_update_read_star_and_delete_state(api_client: TestClient) -> None:
    mark_read = api_client.patch("/entries/article-1/read", json={"is_read": True})
    mark_starred = api_client.patch("/entries/article-1/star", json={"is_starred": True})
    delete_entry = api_client.delete("/entries/article-empty")
    feeds = api_client.get("/feeds")
    tags = api_client.get("/tags")
    entries = api_client.get("/entries")

    assert mark_read.status_code == 200
    assert mark_read.json()["is_read"] is True

    assert mark_starred.status_code == 200
    assert mark_starred.json()["is_starred"] is True

    assert delete_entry.status_code == 200
    assert delete_entry.json() == {"entry_id": "article-empty", "deleted": True}

    assert feeds.status_code == 200
    assert feeds.json()[0]["unread_count"] == 0

    assert tags.status_code == 200
    assert tags.json()[0]["unread_count"] == 0

    assert entries.status_code == 200
    assert [item["id"] for item in entries.json()] == ["article-1"]


def test_cors_preflight_accepts_tauri_origin(api_client: TestClient) -> None:
    response = api_client.options(
        "/feeds/opml/import",
        headers={
            "Origin": "http://tauri.localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"


def test_generate_summary_returns_404_for_missing_entry(api_client: TestClient) -> None:
    response = api_client.post("/agents/summary/generate", json={"entry_id": "missing"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Entry not found"}


def test_generate_summary_returns_409_when_no_content_is_available(api_client: TestClient) -> None:
    response = api_client.post("/agents/summary/generate", json={"entry_id": "article-empty"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Entry has no summary content"}


def test_generate_summary_persists_the_summary_result(api_client: TestClient, monkeypatch) -> None:
    from agent_summary.http import router as summary_router
    from agent_summary.service import SummaryService

    class FakeAgent:
        async def summarize(self, entry_id: str, content: str) -> dict:
            assert content == "Hello Mercury"
            return {
                "entry_id": entry_id,
                "summary_text": "Stored summary",
                "status": "success",
                "provider": "mock",
                "model": "mock-model",
            }

    monkeypatch.setattr(
        summary_router,
        "get_summary_service",
        lambda: SummaryService(agent_factory=FakeAgent),
    )

    response = api_client.post("/agents/summary/generate", json={"entry_id": "article-1"})

    assert response.status_code == 200
    assert response.json() == {
        "entry_id": "article-1",
        "summary_text": "Stored summary",
        "status": "success",
        "provider": "mock",
        "model": "mock-model",
    }

    saved = get_article("article-1")
    assert saved is not None
    assert saved.summary_text == "Stored summary"


def test_generate_summary_returns_500_for_internal_errors(api_db: str, monkeypatch) -> None:
    from agent_summary.http import router as summary_router
    from agent_summary.service import SummaryService

    class FailingAgent:
        async def summarize(self, entry_id: str, content: str) -> dict:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        summary_router,
        "get_summary_service",
        lambda: SummaryService(agent_factory=FailingAgent),
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/agents/summary/generate", json={"entry_id": "article-1"})

    assert response.status_code == 500


def test_generate_summary_surfaces_upstream_llm_errors(api_db: str, monkeypatch) -> None:
    from agent_summary.http import router as summary_router
    from agent_summary.llm_client import LLMClientError
    from agent_summary.service import SummaryService

    class UnauthorizedAgent:
        async def summarize(self, entry_id: str, content: str) -> dict:
            raise LLMClientError(
                "LLM provider rejected the request: 无效的令牌",
                status_code=401,
            )

    monkeypatch.setattr(
        summary_router,
        "get_summary_service",
        lambda: SummaryService(agent_factory=UnauthorizedAgent),
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/agents/summary/generate", json={"entry_id": "article-1"})

    assert response.status_code == 502
    assert response.json() == {"detail": "LLM provider rejected the request: 无效的令牌"}


def _article(article_id: str, reader_html: str) -> Entry:
    return Entry(
        id=article_id,
        feed_id="feed-1",
        title=f"{article_id} title",
        summary="Short summary",
        author="Mercury Team",
        url=f"https://example.com/{article_id}",
        published_at="2026-05-25T08:00:00Z",
        is_read=False,
        is_starred=False,
        tag_ids=[],
        reader_html=reader_html,
        web_preview="",
        related_entry_ids=[],
        note="",
        summary_text="",
        translation_html=None,
        translation_status="idle",
    )
