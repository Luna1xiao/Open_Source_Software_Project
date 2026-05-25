# Mature Storage Hardening

- Member: storage engineer
- Date: 2026-05-25
- Agent: Codex
- Related PR: TBD

## Goal
Harden Mercury storage beyond the first CRUD layer by addressing transaction, batch write, delete/update, tag, agent result, usage, and search risks.

## Approach
Add a second migration for mature storage tables, then extend repositories instead of changing existing contracts. Keep APIs synchronous and sqlite-based so the rest of the backend can continue importing from `db`.

## Decisions
Use batch save functions for common sync paths, explicit repository functions for deletes and article state changes, normalized tag tables, durable agent run/step records, aggregated usage buckets, and a simple search projection table before introducing FTS.

## Surprises
The current schemas are ahead of the initial table model, so several repository functions still project safe defaults until UI and agent contracts become richer.

## Follow-ups
Consider replacing the simple `article_search` projection with SQLite FTS5 after core workflows stabilize.
