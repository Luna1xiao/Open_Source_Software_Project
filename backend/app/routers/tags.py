from fastapi import APIRouter, Query

from app.schemas.tag import Tag
from db import query_tags

router = APIRouter(tags=["tags"])


@router.get("/tags", response_model=list[Tag])
async def get_tags(keyword: str | None = Query(default=None)) -> list[Tag]:
    return query_tags(keyword=keyword)
