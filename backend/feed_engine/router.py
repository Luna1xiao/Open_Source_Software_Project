from __future__ import annotations

import re
from email.parser import BytesParser
from email.policy import default

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.schemas.feed import Feed
from feed_engine.errors import FeedEngineError
from feed_engine.service import (
    delete_feed,
    export_opml,
    import_opml,
    list_feeds,
    parse_feed,
    subscribe_feed,
    sync_all_feeds,
    sync_feed,
)
from feed_engine.types import (
    FeedValidationResult,
    OPMLImportResult,
    ParsedFeed,
    ParseFeedRequest,
    SubscribeFeedRequest,
    SyncResult,
)
from feed_engine.validation import validate_feed_xml

router = APIRouter(prefix="/feeds", tags=["feeds"])


@router.get("", response_model=list[Feed])
async def get_feeds(q: str | None = None) -> list[Feed]:
    return _run_sync(lambda: list_feeds(q))


@router.post("", response_model=Feed)
async def create_feed(request: SubscribeFeedRequest) -> Feed:
    return await _run_async(lambda: subscribe_feed(request.url, sync=request.sync))


@router.post("/parse", response_model=ParsedFeed)
async def parse_feed_url(request: ParseFeedRequest) -> ParsedFeed:
    return await _run_async(lambda: parse_feed(request.url))


@router.post("/validate", response_model=FeedValidationResult)
async def validate_feed(request: Request) -> FeedValidationResult:
    payload = await request.body()
    return _run_sync(lambda: validate_feed_xml(payload))


@router.post("/opml/import", response_model=OPMLImportResult)
async def import_opml_file(request: Request) -> OPMLImportResult:
    try:
        payload = _extract_payload(await request.body(), request.headers.get("content-type", ""))
    except FeedEngineError as exc:
        return _error_response(exc)
    return _run_sync(lambda: import_opml(payload))


@router.get("/opml/export")
async def export_opml_file() -> Response:
    payload = _run_sync(export_opml)
    return Response(
        content=payload,
        media_type="text/x-opml; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="mercury-subscriptions.opml"'},
    )


@router.post("/sync-all", response_model=list[SyncResult])
async def sync_all() -> list[SyncResult]:
    return await _run_async(sync_all_feeds)


@router.post("/{feed_id}/sync", response_model=SyncResult)
async def sync_one(feed_id: str) -> SyncResult:
    return await _run_async(lambda: sync_feed(feed_id))


@router.delete("/{feed_id}")
async def remove_feed(feed_id: str) -> dict[str, bool]:
    return _run_sync(lambda: delete_feed(feed_id))


async def _run_async(call):
    try:
        return await call()
    except FeedEngineError as exc:
        return _error_response(exc)


def _run_sync(call):
    try:
        return call()
    except FeedEngineError as exc:
        return _error_response(exc)


def _error_response(exc: FeedEngineError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.as_detail())


def _extract_payload(body: bytes, content_type: str) -> bytes:
    if "multipart/form-data" not in content_type:
        return body

    match = re.search(r'boundary="?([^";]+)"?', content_type)
    if match is None:
        raise FeedEngineError(
            "OPML_INVALID",
            "Multipart request is missing a boundary.",
            status_code=400,
        )

    boundary = match.group(1).encode("utf-8")
    for part in body.split(b"--" + boundary):
        if not part or part in {b"--\r\n", b"--"}:
            continue
        part = part.strip(b"\r\n")
        if b"\r\n\r\n" not in part:
            continue
        headers_raw, payload = part.split(b"\r\n\r\n", 1)
        message = BytesParser(policy=default).parsebytes(headers_raw + b"\r\n\r\n")
        disposition = message.get("content-disposition", "")
        if "filename=" in disposition or 'name="file"' in disposition:
            return payload.rstrip(b"\r\n")

    raise FeedEngineError(
        "OPML_INVALID",
        "No OPML file part was found.",
        status_code=400,
    )
