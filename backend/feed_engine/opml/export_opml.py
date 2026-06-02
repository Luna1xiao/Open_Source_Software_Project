from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from app.schemas.feed import Feed


def export_opml(feeds: list[Feed]) -> str:
    created = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        "  <head>",
        "    <title>Mercury Subscriptions</title>",
        f"    <dateCreated>{escape(created)}</dateCreated>",
        "  </head>",
        "  <body>",
    ]

    for feed in feeds:
        attrs = {
            "type": "rss",
            "text": feed.title,
            "title": feed.title,
            "xmlUrl": feed.feed_url,
            "htmlUrl": feed.site_url,
        }
        serialized = " ".join(
            f'{name}="{escape(value, quote=True)}"' for name, value in attrs.items() if value
        )
        lines.append(f"    <outline {serialized} />")

    lines.extend(["  </body>", "</opml>"])
    return "\n".join(lines) + "\n"

