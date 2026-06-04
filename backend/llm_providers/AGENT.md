# llm_providers — Agent Guide

**Owner**: member 8 (Platform Engineer)

## Mission

Abstract over LLM providers so summary/translation agents can stay provider-agnostic.
Support any OpenAI-compatible HTTP endpoint, Anthropic's Messages API, and local models
via Ollama. Configuration is persisted (the user adds providers via the settings UI, this
module reads/writes that config).

## Contract (Python)

Suggested module layout:

```
llm_providers/
  __init__.py        re-exports the registry and Protocol
  base.py            LLMProvider protocol (chat, embeddings if needed)
  openai_compatible.py  generic client for any OpenAI-compatible API
  anthropic.py       Anthropic Messages API client
  ollama.py          local provider
  registry.py        load_providers_from_config() / get_provider(name)
  config.py          provider config schema (Pydantic) + persistence
```

Public API:

```python
def get_provider(name: str | None = None) -> LLMProvider: ...
async def list_providers() -> list[ProviderConfig]: ...
async def list_provider_summaries() -> list[ProviderSummary]: ...
async def add_provider(config: ProviderConfig) -> None: ...
async def update_provider(config: ProviderConfig) -> None: ...
async def remove_provider(name: str) -> None: ...
```

`list_provider_summaries()` is safe for settings UI / HTTP responses because it omits
secret values. Use `list_providers()` only inside trusted backend code.

Smoke test:

```bash
cd backend
uv run python -m llm_providers.smoke
uv run python -m llm_providers.smoke --provider deepseek-v4-pro --stream
```

The protocol must be small enough that adding a new provider is straightforward.

## Dependencies

- May add `httpx` (already a dev dep), `ollama-python` (optional).
- May import `db` if config is stored in SQLite, OR persist to a JSON file under `settings.data_dir`.
- Must NOT import `feed_engine`, `content_cleaner`, or `agent_*` (you are below them).
- Must NOT import FastAPI — this is a library.

## Non-Goals

- Prompt templates (live in `agent_summary/` and `agent_translation/`).
- Token accounting beyond raw usage numbers (aggregation is `db/`'s job).
- HTTP endpoints — if a provider config UI is needed, add a small router under `app/` not here.

## Acceptance Criteria

1. Adding a new OpenAI-compatible provider requires only a config entry, no code change.
2. Streaming responses supported (returns an async iterator of chunks).
3. Failures distinguish between auth, network, rate limit, and model errors.
4. Local (Ollama), OpenAI-compatible, and Anthropic providers tested with mock servers.
5. `uv run pytest` and `uv run ruff check` pass.

## Local configuration

Provider entries are stored in `~/.mercury/providers.json`. Copy
`llm_providers/providers.example.json` as a starting point (replace placeholder keys
locally; never commit real secrets).

Example MiMo entry:

```json
{
  "name": "mimo",
  "kind": "openai_compatible",
  "model": "mimo-v2.5-pro",
  "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
  "api_key": "tp-your-mimo-api-key",
  "api_key_header": "api-key",
  "is_default": true
}
```

OpenAI-compatible local gateways use the default `Authorization: Bearer` header and
omit `api_key_header`. Anthropic uses `kind: "anthropic"` and defaults to the `x-api-key`
header. Ollama uses `kind: "ollama"` and talks to `/api/chat`.

Settings UI wiring lives in `packages/ui` and `backend/app/` — this module only
reads/writes the persisted provider registry.

## References

- `app/schemas/agent.py` — request shapes carry optional `provider` and `model` overrides
- `backend/AGENT.md`
