from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.schemas.entry import Entry
from app.schemas.feed import Feed
from db import get_article, init_db, save_article, save_article_content, save_feed


@pytest.fixture
def api_db(tmp_path, monkeypatch) -> Iterator[str]:
    db_path = tmp_path / "mercury-translation-http.db"
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
    save_article(_article("article-1", reader_html="<p>Hello Mercury</p>"), db_path)
    save_article_content(
        article_id="article-1",
        raw_html="<main><p>Hello Mercury</p></main>",
        cleaned_html="<p>Hello Mercury</p>",
        cleaned_markdown="Hello Mercury",
        plain_text="Hello Mercury",
        db_path=db_path,
    )

    yield str(db_path)


@pytest.fixture
def api_client(api_db: str) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


def test_translate_article_uses_mock_fallback_and_persists_result(
    api_client: TestClient,
    monkeypatch,
) -> None:
    import agent_translation.service as translation_service_module
    from agent_translation.http import router as translation_router
    from agent_translation.service import TranslationService

    monkeypatch.setattr(translation_service_module, "_use_mock_llm", lambda: True)
    monkeypatch.setattr(
        translation_router,
        "get_translation_service",
        lambda: TranslationService(),
    )

    response = api_client.post(
        "/agents/translation",
        json={"entry_id": "article-1", "target_lang": "Chinese"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["provider"] == "mock"
    assert '<div class="bilingual-original">Hello Mercury</div>' in payload["translation_html"]
    assert (
        '<div class="bilingual-translation">[Mock Chinese] Hello Mercury</div>'
        in payload["translation_html"]
    )

    saved = get_article("article-1")
    assert saved is not None
    assert payload["translation_html"] == saved.translation_html


def test_translate_article_returns_404_for_missing_entry(api_client: TestClient) -> None:
    response = api_client.post(
        "/agents/translation",
        json={"entry_id": "missing", "target_lang": "Chinese"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Entry not found"}


def test_translate_article_returns_409_when_no_content_is_available(api_client: TestClient) -> None:
    save_article(_article("article-empty", reader_html=""), settings.db_path)

    response = api_client.post(
        "/agents/translation",
        json={"entry_id": "article-empty", "target_lang": "Chinese"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Entry has no content to translate"}


def test_translate_article_returns_failure_payload_for_internal_errors(
    api_client: TestClient, monkeypatch
) -> None:
    from agent_translation.http import router as translation_router
    from agent_translation.service import TranslationService

    class FailingAgent:
        async def translate(
            self,
            content: str,
            target_lang: str,
            temperature: float = 0.3,
            bilingual: bool = False,
        ) -> dict:
            raise RuntimeError("boom")

    monkeypatch.setattr(
        translation_router,
        "get_translation_service",
        lambda: TranslationService(agent_factory=FailingAgent),
    )

    response = api_client.post(
        "/agents/translation",
        json={"entry_id": "article-1", "target_lang": "Chinese"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "entry_id": "article-1",
        "target_lang": "Chinese",
        "translation_html": "",
        "status": "failure",
        "provider": "unknown",
        "model": "unknown",
    }


def test_translate_article_falls_back_to_legacy_env_provider_when_registry_is_empty(
    api_client: TestClient, monkeypatch
) -> None:
    from agent_translation.http import router as translation_router
    from agent_translation.service import TranslationService

    async def fake_translate_via_legacy_client(self, content: str, target_lang: str) -> dict:
        assert content == "Hello Mercury"
        assert target_lang == "Chinese"
        return {
            "translated_text": "Translated from legacy env",
            "provider": "legacy-env",
            "model": "legacy-model",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }

    monkeypatch.setattr(
        TranslationService,
        "_translate_via_legacy_client",
        fake_translate_via_legacy_client,
    )
    monkeypatch.setattr(translation_router, "get_translation_service", lambda: TranslationService())

    response = api_client.post(
        "/agents/translation",
        json={"entry_id": "article-1", "target_lang": "Chinese"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "entry_id": "article-1",
        "target_lang": "Chinese",
        "translation_html": "Translated from legacy env",
        "status": "success",
        "provider": "legacy-env",
        "model": "legacy-model",
    }


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
