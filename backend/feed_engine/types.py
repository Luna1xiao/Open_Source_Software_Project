from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.feed import Feed


class FeedIssue(BaseModel):
    code: str
    message: str
    path: str = ""


class FeedValidationResult(BaseModel):
    valid: bool
    format: str
    errors: list[FeedIssue] = Field(default_factory=list)
    warnings: list[FeedIssue] = Field(default_factory=list)


class ParsedEntry(BaseModel):
    source_id: str
    title: str
    summary: str = ""
    author: str = ""
    url: str = ""
    published_at: str = ""
    raw_html: str = ""


class ParsedFeed(BaseModel):
    title: str
    site_url: str = ""
    feed_url: str
    format: str
    entries: list[ParsedEntry] = Field(default_factory=list)


class FetchMetadata(BaseModel):
    final_url: str
    etag: str | None = None
    last_modified: str | None = None


class ParseFeedRequest(BaseModel):
    url: str


class SubscribeFeedRequest(BaseModel):
    url: str
    sync: bool = True


class SyncResult(BaseModel):
    feed_id: str
    status: str
    fetched: int
    saved: int
    skipped: int = 0
    not_modified: bool = False


class OPMLImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[FeedIssue] = Field(default_factory=list)
    feeds: list[Feed] = Field(default_factory=list)

