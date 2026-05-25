# Storage Engineer Guide

- Member: storage engineer
- Date: 2026-05-25
- Agent: Codex
- Related PR: TBD

## Goal
Create a practical from-zero guide for Mercury's storage engineer to implement cross-platform SQLite persistence and useful Coding Agent trace documentation.

## Approach
Read the existing repository layout, backend stack, `backend/db/AGENT.md`, app config, schemas, and trace rules. Turn the project assignment into an implementation guide aligned with FastAPI, Pydantic, SQLite, `uv`, and the current module boundaries.

## Decisions
Recommend stdlib `sqlite3` first because it is cross-platform and already available with Python 3.11. Use `pathlib` plus `settings.resolved_db_path()` for platform-neutral storage paths. Split article metadata from article content so list queries stay lightweight. Store `agent_runs` and `agent_steps` separately so final Agent outputs and detailed execution traces are both persistent.

## Surprises
The repository already had a dedicated `.agent-traces/` directory and `backend/db/AGENT.md`, so the guide could be made repository-specific instead of generic.

## Follow-ups
Implement the actual `backend/db` connection, migrations, repositories, and tests in a later change.
