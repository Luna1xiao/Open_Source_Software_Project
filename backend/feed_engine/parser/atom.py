from __future__ import annotations

from xml.etree.ElementTree import Element

from feed_engine.parser.dates import parse_date
from feed_engine.parser.xml_utils import child, children, first_text, html_text
from feed_engine.types import ParsedEntry, ParsedFeed


def _atom_link(element: Element) -> str:
    fallback = ""
    for link in children(element, "link"):
        href = link.attrib.get("href", "").strip()
        if not href:
            continue
        if not fallback:
            fallback = href
        if link.attrib.get("rel", "alternate") == "alternate":
            return href
    return fallback


def parse_atom(root: Element, feed_url: str) -> ParsedFeed:
    title = first_text(root, "title") or feed_url
    site_url = _atom_link(root)
    entries: list[ParsedEntry] = []

    for item in children(root, "entry"):
        entry_id = first_text(item, "id")
        url = _atom_link(item)
        author = ""
        author_node = child(item, "author")
        if author_node is not None:
            author = first_text(author_node, "name") or html_text(author_node)

        content = html_text(child(item, "content"))
        summary = html_text(child(item, "summary"))
        title_text = first_text(item, "title") or url or entry_id or "Untitled"
        entries.append(
            ParsedEntry(
                source_id=entry_id or url or title_text,
                title=title_text,
                summary=summary,
                author=author,
                url=url,
                published_at=parse_date(
                    first_text(item, "published") or first_text(item, "updated")
                ),
                raw_html=content or summary,
            )
        )

    return ParsedFeed(
        title=title,
        site_url=site_url,
        feed_url=feed_url,
        format="atom",
        entries=entries,
    )
