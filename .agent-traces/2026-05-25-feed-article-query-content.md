# Feed Article Query Content

- Member: storage engineer
- Date: 2026-05-25
- Agent: Codex
- Related PR: TBD

## Goal
Extend the initial repository layer with feed querying, article listing, and article content updates for the cleaner pipeline.

## Approach
Build on the existing synchronous sqlite repositories. Add keyword search for feeds, paged article listing with optional feed filtering, and a content upsert that writes raw HTML, cleaned HTML, Markdown, plain text, and an optional content hash.

## Decisions
Map article rows through one helper so `get_article()` and `list_articles()` stay consistent. Keep `save_article_content()` separate from `save_article()` because content cleaning is a later pipeline step and should not require rewriting article metadata.

## Surprises
The current `Entry` schema is richer than the first storage schema, so list results still use safe defaults for tags, related entries, previews, and missing agent outputs.

## Follow-ups
Add explicit article content read APIs, pagination tests for offset/limit, and agent result persistence.
