from __future__ import annotations

from xml.etree.ElementTree import Element

from feed_engine.parser.dates import parse_date
from feed_engine.parser.xml_utils import child, children, first_text, html_text
from feed_engine.types import ParsedEntry, ParsedFeed


def parse_rss(root: Element, feed_url: str) -> ParsedFeed:
    channel = child(root, "channel")
    if channel is None:
        return ParsedFeed(title=feed_url, feed_url=feed_url, format="rss2")

    title = first_text(channel, "title") or feed_url
    site_url = first_text(channel, "link")
    entries: list[ParsedEntry] = []

    for item in children(channel, "item"):
        content = html_text(child(item, "encoded")) or html_text(child(item, "content"))
        summary = html_text(child(item, "description"))
        url = first_text(item, "link")
        guid = first_text(item, "guid")
        title_text = first_text(item, "title") or url or guid or "Untitled"
        entries.append(
            ParsedEntry(
                source_id=guid or url or title_text,
                title=title_text,
                summary=summary,
                author=first_text(item, "creator") or first_text(item, "author"),
                url=url,
                published_at=parse_date(first_text(item, "pubDate")),
                raw_html=content or summary,
            )
        )

    return ParsedFeed(
        title=title,
        site_url=site_url,
        feed_url=feed_url,
        format="rss2",
        entries=entries,
    )

