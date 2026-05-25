# Storage Integration Hardening

- Member: storage engineer
- Date: 2026-05-25
- Agent: Codex
- Related PR: TBD

## Goal
Add cross-module storage integration coverage and tighten API documentation, agent status consistency, search projection freshness, and cascade delete guarantees.

## Approach
Create an integration test that simulates Feed, Cleaner, TagAgent, SummaryAgent, and readback consumers. Add concise docstrings for key repository APIs. Add a trigger-based migration to reject invalid agent run statuses without rebuilding the existing table.

## Decisions
Use SQLite triggers for status constraints because SQLite cannot safely add a CHECK constraint to an existing column without table rebuild work. Keep the integration test at repository level so it runs fast and does not depend on network or HTTP routes.

## Surprises
The existing schema already had foreign-key cascade definitions, so the hardening work focused on proving the behavior with tests instead of changing the original table definitions.

## Follow-ups
Add `get_article_content`, provider settings repository, app config repository, and usage query APIs in future storage iterations.
