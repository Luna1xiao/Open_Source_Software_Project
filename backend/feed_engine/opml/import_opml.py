from __future__ import annotations

from xml.etree.ElementTree import ParseError, fromstring

from app.schemas.feed import Feed
from feed_engine.errors import FeedEngineError
from feed_engine.ids import make_feed_id, normalize_url
from feed_engine.parser.xml_utils import descendants, local_name
from feed_engine.types import FeedIssue


def parse_opml(payload: str | bytes) -> tuple[list[Feed], list[FeedIssue]]:
    try:
        root = fromstring(payload)
    except ParseError as exc:
        raise FeedEngineError(
            "OPML_INVALID",
            "OPML file could not be parsed.",
            status_code=400,
            context={"reason": str(exc)},
        ) from exc

    if local_name(root.tag) != "opml":
        raise FeedEngineError(
            "OPML_INVALID",
            "Uploaded document is not an OPML file.",
            status_code=400,
        )

    feeds: list[Feed] = []
    errors: list[FeedIssue] = []
    seen: set[str] = set()

    for outline in descendants(root, "outline"):
        xml_url = outline.attrib.get("xmlUrl", "").strip()
        if not xml_url:
            continue

        normalized = normalize_url(xml_url)
        if normalized in seen:
            errors.append(
                FeedIssue(
                    code="OPML_DUPLICATE_FEED",
                    message="Duplicate feed URL skipped.",
                    path=xml_url,
                )
            )
            continue

        seen.add(normalized)
        title = (
            outline.attrib.get("title", "").strip()
            or outline.attrib.get("text", "").strip()
            or xml_url
        )
        feeds.append(
            Feed(
                id=make_feed_id(xml_url),
                title=title,
                site_url=outline.attrib.get("htmlUrl", "").strip(),
                feed_url=xml_url,
                unread_count=0,
                status="idle",
            )
        )

    return feeds, errors
