from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from feed_engine.errors import FeedEngineError


@dataclass(frozen=True)
class FetchResponse:
    status_code: int
    final_url: str
    body: bytes
    etag: str | None
    last_modified: str | None
    content_type: str | None


def validate_url(url: str) -> str:
    value = url.strip()
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise FeedEngineError(
            "INVALID_URL",
            "Feed URL must be an absolute http or https URL.",
            status_code=400,
            context={"url": url},
        )
    return value


async def fetch_feed(
    url: str,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    timeout_seconds: float = 15.0,
) -> FetchResponse:
    return await asyncio.to_thread(
        _fetch_feed_sync,
        validate_url(url),
        etag,
        last_modified,
        timeout_seconds,
    )


def _fetch_feed_sync(
    url: str,
    etag: str | None,
    last_modified: str | None,
    timeout_seconds: float,
) -> FetchResponse:
    headers = {
        "User-Agent": "Mercury/0.1 feed-engine",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return FetchResponse(
                status_code=response.status,
                final_url=response.url,
                body=response.read(),
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                content_type=response.headers.get("Content-Type"),
            )
    except HTTPError as exc:
        if exc.code == 304:
            return FetchResponse(
                status_code=304,
                final_url=url,
                body=b"",
                etag=exc.headers.get("ETag"),
                last_modified=exc.headers.get("Last-Modified"),
                content_type=exc.headers.get("Content-Type"),
            )
        raise FeedEngineError(
            "FETCH_FAILED",
            "Feed server returned an error.",
            status_code=502,
            context={"url": url, "status": exc.code},
        ) from exc
    except TimeoutError as exc:
        raise FeedEngineError(
            "FETCH_TIMEOUT",
            "Feed request timed out.",
            status_code=504,
            context={"url": url},
        ) from exc
    except (URLError, OSError) as exc:
        raise FeedEngineError(
            "FETCH_FAILED",
            "Feed request failed.",
            status_code=502,
            context={"url": url, "reason": str(exc)},
        ) from exc
