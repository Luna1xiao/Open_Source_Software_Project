from __future__ import annotations

from feed_engine.parser.detect import detect_format, parse_xml
from feed_engine.parser.xml_utils import child, children, first_text
from feed_engine.types import FeedIssue, FeedValidationResult


def validate_feed_xml(xml: str | bytes) -> FeedValidationResult:
    root = parse_xml(xml)
    feed_format = detect_format(root)
    errors: list[FeedIssue] = []
    warnings: list[FeedIssue] = []

    if feed_format == "unknown":
        errors.append(
            FeedIssue(
                code="UNSUPPORTED_FEED",
                message="Only RSS 2.0 and Atom feeds are supported.",
                path="/",
            )
        )
        return FeedValidationResult(valid=False, format=feed_format, errors=errors)

    if feed_format == "rss2":
        channel = child(root, "channel")
        if channel is None:
            errors.append(FeedIssue(code="RSS_CHANNEL_MISSING", message="RSS channel is missing."))
        else:
            if not first_text(channel, "title"):
                warnings.append(
                    FeedIssue(code="FEED_TITLE_MISSING", message="Feed title is missing.")
                )
            if not children(channel, "item"):
                warnings.append(FeedIssue(code="FEED_ITEMS_EMPTY", message="Feed has no items."))

    if feed_format == "atom":
        if not first_text(root, "title"):
            warnings.append(FeedIssue(code="FEED_TITLE_MISSING", message="Feed title is missing."))
        if not children(root, "entry"):
            warnings.append(FeedIssue(code="FEED_ITEMS_EMPTY", message="Feed has no entries."))

    return FeedValidationResult(
        valid=not errors,
        format=feed_format,
        errors=errors,
        warnings=warnings,
    )
