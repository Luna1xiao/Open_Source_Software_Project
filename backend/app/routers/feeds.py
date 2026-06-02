from fastapi import APIRouter, Query

from app.schemas.feed import Feed
from db import query_feeds

router = APIRouter(tags=["feeds"])


@router.get("/feeds", response_model=list[Feed])
async def get_feeds(keyword: str | None = Query(default=None)) -> list[Feed]:
    return query_feeds(keyword=keyword)
