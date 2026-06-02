# Feed Engine Backend Implementation

- Member: tuziTZ
- Date: 2026-05-26
- Agent: Codex
- Related PR: TBD

## Goal
Implement Mercury's Feed Engineer module directly in `backend/feed_engine`, covering RSS 2.0, Atom, OPML import/export, validation, and sync entry points while respecting the storage API documented by the DB engineer.

## Approach
Kept parser logic pure and testable, then added a service layer that converts parsed feeds into `app.schemas.Feed` and `app.schemas.Entry`. FastAPI routes are thin wrappers that map `FeedEngineError` into structured HTTP errors. Storage access is runtime-loaded from `db` so the app can still start while `backend/db/__init__.py` is pending implementation.

## Decisions
Skipped `packages/feed-engine` because the storage contract is Python-only. Avoided new runtime dependencies and used stdlib XML/HTTP utilities. OPML upload accepts raw XML or multipart bytes without requiring `python-multipart`.

## Surprises
The storage README exists, but the exported repository functions are not implemented yet. The local machine also lacked `uv`, so validation used `python -m pytest` and `python -m ruff check`.

## Follow-ups
Regenerate frontend OpenAPI types once `uv` is available or CI runs `pnpm gen:types`. Wire real DB repository implementations for feed sync metadata and article persistence.
