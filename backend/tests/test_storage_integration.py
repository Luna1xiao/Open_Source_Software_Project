from app.schemas.agent import SummaryResult
from app.schemas.entry import Entry
from app.schemas.feed import Feed
from app.schemas.tag import Tag
from db import (
    get_article,
    init_db,
    list_articles,
    query_feeds,
    save_agent_result,
    save_article_content,
    save_articles,
    save_feed,
    save_tag,
    search_articles,
    set_article_tags,
)


def test_feed_cleaner_agent_storage_pipeline(tmp_path) -> None:
    db_path = tmp_path / "mercury-test.db"
    init_db(db_path)

    feed = Feed(
        id="feed-storage",
        title="Storage Team Feed",
        site_url="https://storage.example.com",
        feed_url="https://storage.example.com/rss.xml",
        unread_count=0,
        status="success",
    )
    article = Entry(
        id="article-storage-1",
        feed_id="feed-storage",
        title="Storage pipeline works",
        summary="Feed engineer parsed this RSS entry.",
        author="Feed Engineer",
        url="https://storage.example.com/articles/1",
        published_at="2026-05-25T10:00:00Z",
        is_read=False,
        is_starred=False,
        tag_ids=[],
        reader_html="",
        web_preview="",
        related_entry_ids=[],
        note="",
        summary_text="",
        translation_html=None,
        translation_status="idle",
    )

    save_feed(feed, db_path)
    save_articles([article], db_path)

    save_article_content(
        article_id="article-storage-1",
        raw_html="<main><h1>Storage</h1><p>Cleaner wrote this content.</p></main>",
        cleaned_html="<h1>Storage</h1><p>Cleaner wrote this content.</p>",
        cleaned_markdown="# Storage\n\nCleaner wrote this content.",
        plain_text="Storage\nCleaner wrote this content.",
        content_hash="hash-storage-1",
        db_path=db_path,
    )

    save_tag(
        Tag(id="tag-storage", name="Storage", aliases=["sqlite"], usage_count=0, unread_count=0),
        db_path,
    )
    set_article_tags("article-storage-1", ["tag-storage"], db_path)

    save_agent_result(
        SummaryResult(
            entry_id="article-storage-1",
            summary_text="The storage pipeline is connected end to end.",
            status="success",
            provider="mock",
            model="mock-summary",
        ),
        db_path,
    )

    feeds = query_feeds(db_path=db_path)
    feed_articles = list_articles(feed_id="feed-storage", db_path=db_path)
    tagged_articles = list_articles(tag_id="tag-storage", db_path=db_path)
    saved_article = get_article("article-storage-1", db_path)
    search_results = search_articles("Cleaner", db_path=db_path)

    assert feeds == [
        Feed(
            id=feed.id,
            title=feed.title,
            site_url=feed.site_url,
            feed_url=feed.feed_url,
            unread_count=1,
            status=feed.status,
        )
    ]
    assert [entry.id for entry in feed_articles] == ["article-storage-1"]
    assert [entry.id for entry in tagged_articles] == ["article-storage-1"]
    assert saved_article is not None
    assert saved_article.reader_html == "<h1>Storage</h1><p>Cleaner wrote this content.</p>"
    assert saved_article.tag_ids == ["tag-storage"]
    assert saved_article.summary_text == "The storage pipeline is connected end to end."
    assert [entry.id for entry in search_results] == ["article-storage-1"]
