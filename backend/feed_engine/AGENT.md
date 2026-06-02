# feed_engine Agent Guide

**Owner**: member 2 (Feed Engineer)

## Mission

Provide RSS/Atom/OPML parsing, feed sync, and import/export over HTTP. This is the
only place that talks to the public internet to fetch feed XML.

Implementation lives directly in `backend/feed_engine/`. Do not route this work
through `packages/feed-engine`.

## Contract (HTTP)

Mounted at `/feeds`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/feeds` | list all subscribed feeds, optional `?q=` |
| `POST` | `/feeds` | subscribe by URL |
| `DELETE` | `/feeds/{feed_id}` | unsubscribe |
| `POST` | `/feeds/parse` | fetch and parse a feed without saving |
| `POST` | `/feeds/validate` | validate RSS/Atom XML body |
| `POST` | `/feeds/{feed_id}/sync` | fetch and persist entries |
| `POST` | `/feeds/sync-all` | sync every feed |
| `POST` | `/feeds/opml/import` | import OPML file or raw XML body |
| `GET` | `/feeds/opml/export` | download OPML file |

Use `app.schemas.Feed` and `app.schemas.Entry`. Do not redefine these.

## Dependencies

- May import from `db` for entry/feed persistence.
- Must use storage repository functions documented in `backend/db/README.md`.
- Must NOT write SQL directly.
- Must NOT import `content_cleaner` directly; entries are stored raw and cleaning happens on read.
- Must NOT import any `agent_*` module.

## Non-Goals

- HTML cleaning / Markdown conversion (that's `content_cleaner`).
- Summary or translation (those are `agent_*`).
- Any UI concerns.

## Acceptance Criteria

1. `GET /feeds` returns valid `Feed` objects matching the Pydantic schema.
2. `POST /feeds/{feed_id}/sync` is idempotent; re-syncing does not create duplicate entries.
3. OPML import handles nested `<outline>` groups.
4. Network errors surface as `502` or `504` with a structured error body, not 500.
5. Unit tests cover the parser with at least one RSS 2.0, one Atom, and one OPML fixture.
6. `uv run pytest` and `uv run ruff check` pass.

## References

- `app/schemas/feed.py` and `app/schemas/entry.py` - authoritative shapes
- `backend/db/README.md` - storage API contract
- `backend/feed_engine/readme.md` - implementation and handoff guide
- `backend/AGENT.md` - workspace-level rules
- `packages/ui/src/domain/fixtures.ts` - UI data expectations

