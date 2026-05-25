# Storage Completeness APIs

- Member: storage engineer
- Date: 2026-05-25
- Agent: Codex
- Related PR: TBD

## Goal
Close remaining storage gaps with article content reads, feed sync metadata updates, provider settings, app config, usage queries, FTS search, migration compatibility coverage, session support, and database backup.

## Approach
Add narrow repository APIs while preserving existing imports from `db`. Use Pydantic for article content, dict JSON APIs for provider/app config, UsageBucket for usage queries, and SQLite FTS5 for article search with the existing LIKE path as fallback.

## Decisions
Keep OPML and Markdown export out of the storage layer for now because they are higher-level product/export workflows. Provide database backup at the storage layer because it is local-first infrastructure.

## Surprises
FTS5 can be added with a virtual table and triggers over the existing article_search projection, so the public `search_articles()` API did not need to change.

## Follow-ups
Add route-level wrappers for provider settings and app config once frontend settings screens are ready.
