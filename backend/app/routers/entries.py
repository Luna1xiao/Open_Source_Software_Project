from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.entry import Entry, EntryDeleteResult, EntryReadStateRequest, EntryStarStateRequest
from db import delete_article, get_article, list_articles, mark_article_read, mark_article_starred, search_articles

router = APIRouter(tags=["entries"])


@router.get("/entries", response_model=list[Entry])
async def get_entries(
    feed_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Entry]:
    entries = (
        search_articles(keyword, limit=limit, offset=offset)
        if keyword
        else list_articles(feed_id=feed_id, limit=limit, offset=offset)
    )
    if keyword and feed_id is not None:
        entries = [entry for entry in entries if entry.feed_id == feed_id]
    return entries


@router.get("/entries/{entry_id}", response_model=Entry)
async def get_entry(entry_id: str) -> Entry:
    entry = get_article(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.patch("/entries/{entry_id}/read", response_model=Entry)
async def set_entry_read_state(entry_id: str, request: EntryReadStateRequest) -> Entry:
    updated = mark_article_read(entry_id, request.is_read)
    if not updated:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = get_article(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.patch("/entries/{entry_id}/star", response_model=Entry)
async def set_entry_star_state(entry_id: str, request: EntryStarStateRequest) -> Entry:
    updated = mark_article_starred(entry_id, request.is_starred)
    if not updated:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = get_article(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.delete("/entries/{entry_id}", response_model=EntryDeleteResult)
async def remove_entry(entry_id: str) -> EntryDeleteResult:
    deleted = delete_article(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    return EntryDeleteResult(entry_id=entry_id, deleted=True)
