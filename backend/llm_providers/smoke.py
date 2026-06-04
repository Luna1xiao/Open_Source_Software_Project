"""Smoke-test configured providers from ~/.mercury/providers.json."""

from __future__ import annotations

import argparse
import asyncio

from llm_providers import ChatMessage, ChatOptions, get_provider, list_provider_summaries


async def run(provider_name: str | None, stream: bool) -> int:
    summaries = await list_provider_summaries()
    if not summaries:
        print("No providers configured. Copy providers.example.json to ~/.mercury/providers.json")
        return 1

    print("Configured providers:")
    for summary in summaries:
        marker = " (default)" if summary.is_default else ""
        print(f"- {summary.name}: {summary.kind} / {summary.model}{marker}")

    provider = get_provider(provider_name)
    messages = [ChatMessage(role="user", content="Reply with exactly: ok")]
    options = ChatOptions(temperature=0.7, max_completion_tokens=64)

    print(f"\nTesting provider: {provider.name} / {provider.model}")
    if stream:
        chunks: list[str] = []
        stream_iter = await provider.chat(messages, stream=True, options=options)
        async for chunk in stream_iter:
            chunks.append(chunk)
            print(chunk, end="", flush=True)
        print()
        print(f"stream joined: {''.join(chunks)!r}")
    else:
        result = await provider.chat(messages, stream=False, options=options)
        print(f"model: {result.model}")
        print(f"usage: {result.usage.model_dump()}")
        print(f"content: {result.content}")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test llm_providers registry")
    parser.add_argument("--provider", help="Provider name (defaults to configured default)")
    parser.add_argument("--stream", action="store_true", help="Use streaming mode")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.provider, args.stream)))


if __name__ == "__main__":
    main()
