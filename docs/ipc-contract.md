# IPC Contract

The frontend and backend communicate over HTTP on localhost. This document is the canonical list of endpoints, kept in sync with `backend/app/main.py` and the per-module routers.

## Base URL

- Dev: `http://127.0.0.1:8000`
- Packaged: `http://127.0.0.1:${window.__BACKEND_PORT__}` (set by the Tauri shell at boot)

## Type Sync

All request/response shapes are Pydantic models in `backend/app/schemas/`. The TS frontend imports them from `@mercury/shared-types`, which is regenerated from `/openapi.json`.

After changing any model or route signature:

```bash
pnpm gen:types
```

Commit the updated `packages/shared-types/src/generated.ts` in the same PR.

## Endpoint Table

Owners populate this table as endpoints land. Format: `METHOD path → response`.

### Meta (tech lead)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| GET | `/healthz` | — | `{ status: "ok" }` | liveness probe |

### Feeds (member 2)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| GET | `/feeds` | — | `Feed[]` | owner: feed module, side effects: none |
| POST | `/feeds` | `SubscribeFeedRequest` | `Feed` | owner: feed module, side effects: creates a feed and optionally fetches entries |
| POST | `/feeds/opml/import` | raw OPML XML | `OPMLImportResult` | owner: feed module, side effects: imports feed subscriptions only |
| POST | `/feeds/sync-all` | — | `SyncResult[]` | owner: feed module, side effects: fetches and stores latest entries for all feeds |

### Tags (frontend-facing read API)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| GET | `/tags` | — | `Tag[]` | owner: tag read API, side effects: none |

### Entries (frontend-facing read API)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| GET | `/entries?feed_id=&keyword=&limit=&offset=` | — | `Entry[]` | owner: entry read API, side effects: none |
| GET | `/entries/{entry_id}` | — | `Entry` | owner: entry read API, side effects: none |

### Content (member 4)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| GET | `/content/entries/{article_id}/clean` | — | `CleanContentResponse` | owner: content cleaner, side effects: cleans and persists article content |

### Summary Agent (member 6)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| POST | `/agents/summary/generate` | `SummaryRequest` | `SummaryResult` | owner: summary agent, side effects: persists the generated summary |

### Translation Agent (member 7)

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| (planned) | `/agents/translation/*` | | | see `backend/agent_translation/AGENT.md` |

## Schemas Used by the UI

```ts
type Feed = {
  id: string;
  title: string;
  site_url: string;
  feed_url: string;
  unread_count: number;
  status: "idle" | "queued" | "running" | "success" | "failure" | "cancelled";
};

type Tag = {
  id: string;
  name: string;
  aliases: string[];
  usage_count: number;
  unread_count: number;
};

type Entry = {
  id: string;
  feed_id: string;
  title: string;
  summary: string;
  author: string;
  url: string;
  published_at: string;
  is_read: boolean;
  is_starred: boolean;
  tag_ids: string[];
  reader_html: string;
  web_preview: string;
  related_entry_ids: string[];
  note: string;
  summary_text: string;
  translation_html?: string | null;
  translation_status: "idle" | "queued" | "running" | "success" | "failure" | "cancelled";
};

type SummaryRequest = {
  entry_id: string;
  provider?: string | null;
  model?: string | null;
};

type SummaryResult = {
  entry_id: string;
  summary_text: string;
  status: "idle" | "queued" | "running" | "success" | "failure" | "cancelled";
  provider: string;
  model: string;
};

type SubscribeFeedRequest = {
  url: string;
  sync?: boolean;
};

type SyncResult = {
  feed_id: string;
  status: string;
  fetched: number;
  saved: number;
  skipped?: number;
  not_modified?: boolean;
};

type OPMLImportResult = {
  imported: number;
  skipped: number;
  errors: Array<{ code: string; message: string; path?: string }>;
  feeds: Feed[];
};

type CleanContentResponse = {
  article_id?: string | null;
  cleaned_html: string;
  cleaned_markdown: string;
  plain_text: string;
  content_hash?: string | null;
  word_count: number;
  reading_time_minutes: number;
};
```

## Endpoint Details

### `GET /feeds`

- Query: `keyword?`
- Success: returns all feeds, sorted by title, including unread counts
- Errors: `500` on backend/storage failure
- Side effects: none

### `POST /feeds`

- Purpose: subscribe to one feed URL from the UI
- Request fields:
  - `url`: required, feed URL
  - `sync?`: optional, defaults to `true`; when true the backend fetches entries immediately
- Success: returns the stored `Feed`
- Errors:
  - `400`: invalid feed URL or unsupported feed payload
  - `422`: FastAPI validation error payload
  - `500`: backend/storage/fetch failure
- Side effects:
  - persists the feed
  - when `sync=true`, fetches and stores entries in the same request

### `POST /feeds/opml/import`

- Purpose: import feed subscriptions from a local OPML file
- Request body: raw OPML XML with `Content-Type: text/x-opml` or multipart file upload
- Success response fields:
  - `imported`: number of newly stored feeds
  - `skipped`: number of duplicate feeds skipped
  - `errors`: parse errors for malformed outlines
  - `feeds`: imported feeds
- Errors:
  - `400`: malformed OPML payload or missing multipart file part
  - `500`: backend/storage failure
- Side effects:
  - persists feed subscriptions only
  - does not fetch entries; call `/feeds/sync-all` afterwards

### `POST /feeds/sync-all`

- Purpose: fetch the latest entries for every stored feed
- Success: returns one `SyncResult` per feed
- Errors:
  - `500`: backend/fetch/storage failure
- Side effects:
  - network fetches remote feed XML
  - upserts article metadata and raw article HTML projections

### `GET /tags`

- Query: `keyword?`
- Success: returns all tags, including aliases, usage count, and unread count
- Errors: `500` on backend/storage failure
- Side effects: none

### `GET /entries`

- Query:
  - `feed_id?`: restrict entries to one feed
  - `keyword?`: text search across title/summary/content projection
  - `limit`: default `50`
  - `offset`: default `0`
- Success: returns newest-first entry list
- Errors: `500` on backend/storage failure
- Side effects: none

### `GET /entries/{entry_id}`

- Path:
  - `entry_id`: backend article id
- Success: returns one entry, including `summary_text`
- Errors:
  - `404`: `{ "detail": "Entry not found" }`
  - `500`: backend/storage failure
- Side effects: none

### `GET /content/entries/{article_id}/clean`

- Purpose: clean stored raw article HTML into reader HTML + Markdown
- Path:
  - `article_id`: backend article id
- Success response fields:
  - `cleaned_html`: sanitized reader HTML persisted back into storage
  - `cleaned_markdown`: markdown projection used by agents
  - `plain_text`: search/plain-text projection
  - `word_count`: computed word count
  - `reading_time_minutes`: estimated reading time
- Errors:
  - `404`: `{ "detail": "Article '<id>' not found" }`
  - `500`: cleaner or storage internal error
- Side effects:
  - persists cleaned content into `article_content`
  - subsequent `GET /entries/{entry_id}` reflects updated `reader_html`

### `POST /agents/summary/generate`

- Purpose: generate and persist a summary for an existing entry
- Request fields:
  - `entry_id`: required, target entry id
  - `provider?`: optional provider hint; currently reserved for future routing
  - `model?`: optional model hint; currently reserved for future routing
- Success response fields:
  - `entry_id`: summarized entry id
  - `summary_text`: generated summary text
  - `status`: long-task status, currently `success` on completion
  - `provider`: provider recorded for this run
  - `model`: model recorded for this run
- Errors:
  - `404`: `{ "detail": "Entry not found" }`
  - `409`: `{ "detail": "Entry has no summary content" }`
  - `422`: FastAPI validation error payload
  - `500`: agent or storage internal error
- Side effects:
  - runs the summary agent
  - persists the completed result into storage
  - subsequent `GET /entries/{entry_id}` reflects the new `summary_text`

`curl` example:

```bash
curl -X POST http://127.0.0.1:8000/agents/summary/generate \
  -H "Content-Type: application/json" \
  -d '{"entry_id":"article-1"}'
```

Frontend wrapper example:

```ts
import { createClient, generateSummary } from "@mercury/ipc-client";

const client = createClient({ baseUrl: "http://127.0.0.1:8000" });
const result = await generateSummary(client, { entry_id: "article-1" });
console.log(result.summary_text);
```

## Breaking-Change Policy

A breaking change is:
- Removing or renaming a route, query param, or response field
- Changing a response field's type
- Making a previously-optional field required

Before merging a breaking change:
1. Coordinate with the UI engineer (member 5) and any downstream module owners
2. Update both the backend and the UI in the same PR (or in two sequenced PRs the same day)
3. Note the change in the PR description

Additions (new endpoint, new optional field) are non-breaking and do not require coordination beyond review.

## Error Format

Application-level errors used by the current UI return:

```json
{
  "detail": "human-readable message"
}
```

- `404` for missing resources
- `409` for valid requests that cannot be completed with current data
- `422` for FastAPI validation errors
- `5xx` for internal errors

FastAPI validation errors still use the framework default `{"detail": [...]}` shape.
