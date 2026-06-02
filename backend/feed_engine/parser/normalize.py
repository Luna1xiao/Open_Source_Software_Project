from __future__ import annotations

from xml.etree.ElementTree import Element

from feed_engine.errors import FeedEngineError
from feed_engine.parser.atom import parse_atom
from feed_engine.parser.detect import detect_format
from feed_engine.parser.rss import parse_rss
from feed_engine.types import ParsedFeed


def parse_feed_root(root: Element, feed_url: str) -> ParsedFeed:
    feed_format = detect_format(root)
    if feed_format == "rss2":
        return parse_rss(root, feed_url)
    if feed_format == "atom":
        return parse_atom(root, feed_url)

    raise FeedEngineError(
        "UNSUPPORTED_FEED",
        "Only RSS 2.0 and Atom feeds are supported.",
        status_code=400,
        context={"root": root.tag},
    )

