# Storage DB Skeleton

- Member: storage engineer
- Date: 2026-05-25
- Agent: Codex
- Related PR: TBD

## Goal
Implement the first Mercury storage-layer skeleton: SQLite connection setup, initial schema migration, `init_db` export, app startup initialization, and a minimal table-creation test.

## Approach
Use Python stdlib `sqlite3` to avoid extra runtime dependencies. Keep schema in versioned SQL under `backend/db/schema/`, expose `init_db()` from `backend/db/__init__.py`, and call it from FastAPI lifespan so local databases are initialized on startup.

## Decisions
Enable foreign keys, WAL, busy timeout, and normal synchronous mode for every connection. Use a tmp-path database in the migration test instead of a real user database so tests stay isolated and cross-platform.

## Surprises
The local environment does not have `uv`, `pytest`, or `pydantic_settings` available, so full test execution was blocked. Python `compileall` passed, which verifies syntax, but dependency installation is still needed for the real test command.

## Follow-ups
Install backend dependencies with `uv sync`, then run `uv run pytest` and `uv run ruff check`.
