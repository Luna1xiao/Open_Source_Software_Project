from __future__ import annotations

import asyncio

from agent_summary.agent.summary_agent import MockLLM


def test_mock_llm_returns_content_based_summary() -> None:
    prompt = (
        "请用 2-3 句话总结以下内容：\n\n"
        "The colorful I/O logo sits on a stage. "
        "It highlights Google's annual developer conference."
    )

    summary = asyncio.run(MockLLM().chat(prompt))

    assert "Mock summary for:" not in summary
    assert "The colorful I/O logo sits on a stage." in summary
