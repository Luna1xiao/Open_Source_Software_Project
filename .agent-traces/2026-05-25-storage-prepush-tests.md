# Storage Prepush Tests

- Member: storage engineer
- Date: 2026-05-25
- Agent: Codex
- Related PR: TBD

## Goal
Add extra pre-push tests for storage edge cases that are likely to matter during team integration.

## Approach
Cover missing-record behavior, feed metadata misses, failed agent runs, translation language filtering, agent step ordering, usage filters, FTS indexing across title/summary/plain text, storage session rollback, provider updates, and app config updates.

## Decisions
Keep these tests at repository level so they stay fast and deterministic. Avoid network, HTTP, or UI dependencies.

## Surprises
The existing tests already covered the happy paths well, so the new file focuses on boundary and regression scenarios.

## Follow-ups
Run `uv run ruff check` and `uv run pytest` before pushing.
