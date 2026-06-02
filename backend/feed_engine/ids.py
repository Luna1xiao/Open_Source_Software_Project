from __future__ import annotations

from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from feed_engine.types import ParsedEntry


def normalize_url(url: str) -> str:
    value = url.strip()
    if not value:
        return ""

    parts = urlsplit(value)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"
    query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit((scheme, netloc, path, query, ""))


def stable_hash(value: str, length: int = 24) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:length]


def make_feed_id(feed_url: str) -> str:
    return f"feed-{stable_hash(normalize_url(feed_url), 16)}"


def make_entry_id(feed_id: str, entry: ParsedEntry) -> str:
    source = entry.source_id or normalize_url(entry.url)
    if not source:
        source = f"{entry.title}|{entry.published_at}"
    return f"article-{stable_hash(f'{feed_id}|{source}', 24)}"

