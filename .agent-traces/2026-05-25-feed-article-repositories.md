# Feed Article Repositories

- Member: storage engineer
- Date: 2026-05-25
- Agent: Codex
- Related PR: TBD

## Goal
Add the first storage repositories for Mercury feeds and articles, including minimal save/get CRUD functions and tests.

## Approach
Keep repository functions small and synchronous on top of stdlib `sqlite3`. Accept an optional `db_path` so unit tests can use isolated temporary databases while application code can rely on the default configured path.

## Decisions
Return Pydantic `Feed` and `Entry` models instead of raw SQLite rows. Store article display HTML in `article_content.cleaned_html` for now because the current `Entry` schema exposes `reader_html` but the body table is already separated from article metadata.

## Surprises
The current `Entry` model contains fields that do not yet have dedicated tables, such as tags and related entries. The initial repository returns safe defaults for those fields until their modules are implemented.

## Follow-ups
Add list/query APIs, tag persistence, article content CRUD, and agent result repositories after the basic feed/article path is stable.
