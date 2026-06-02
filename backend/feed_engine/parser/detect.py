from __future__ import annotations

from xml.etree.ElementTree import Element, ParseError, fromstring

from feed_engine.errors import FeedEngineError
from feed_engine.parser.xml_utils import local_name


def parse_xml(xml: str | bytes) -> Element:
    try:
        return fromstring(xml)
    except ParseError as exc:
        raise FeedEngineError(
            "INVALID_XML",
            "Feed XML could not be parsed.",
            status_code=400,
            context={"reason": str(exc)},
        ) from exc


def detect_format(root: Element) -> str:
    name = local_name(root.tag)
    if name == "rss":
        return "rss2"
    if name == "feed":
        return "atom"
    return "unknown"

