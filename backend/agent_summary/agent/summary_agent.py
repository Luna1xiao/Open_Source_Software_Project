"""SummaryAgent 核心实现"""

import re
from time import time
from urllib.parse import urlparse

from ..core.hooks import HookRegistry
from ..core.router import Router
from ..core.state import AgentState
from ..core.tracer import RunResult
from ..llm_client import LLMClient
from ..steps.analyze import AnalyzeStep
from ..steps.evaluate import EvaluateStep
from ..steps.search import SearchStep
from ..steps.summarize import SummarizeStep
from ..tools.base import Tool, ToolRegistry


class MockLLM:
    """Mock LLM 用于测试"""

    async def chat(self, prompt: str) -> str:
        content = _extract_mock_content(prompt)
        if not content:
            return "This article does not contain enough readable content to summarize."

        sentences = [
            segment.strip()
            for segment in re.split(r"(?<=[。！？.!?])\s+", content)
            if segment.strip()
        ]
        if not sentences:
            return _truncate(content, 180)

        first = _truncate(sentences[0], 120)
        second = _truncate(sentences[1], 120) if len(sentences) > 1 else ""
        if second:
            return f"{first}\n\n{second}"
        return first


class SummaryAgent:
    """摘要 Agent"""

    def __init__(self, llm_provider=None, tools: list[Tool] | None = None, use_mock: bool = False):
        # 默认使用真实 LLM，测试时可传入 use_mock=True
        if llm_provider:
            self.llm = llm_provider
            self.provider_name = getattr(
                llm_provider,
                "provider_name",
                _provider_name_from_base_url(getattr(llm_provider, "base_url", "")),
            )
            self.model_name = getattr(llm_provider, "model", "custom")
        elif use_mock:
            self.llm = MockLLM()
            self.provider_name = "mock"
            self.model_name = "mock-summary"
        else:
            self.llm = LLMClient()
            self.provider_name = _provider_name_from_base_url(self.llm.base_url)
            self.model_name = self.llm.model

        self.tools = ToolRegistry()
        self.hooks = HookRegistry()
        self.router = Router()

        # 注册工具
        for t in (tools or []):
            self.tools.register(t)

        # 配置路由
        self._setup_routes()

    def _setup_routes(self):
        """配置条件路由"""
        self.router.add_route(
            lambda s: s.profile is not None and s.profile.needs_context,
            "search"
        )
        self.router.add_route(
            lambda s: s.profile is not None and s.profile.length > 8000,
            "hierarchical"
        )
        self.router.add_route(lambda s: True, "direct")

    async def run(self, state: AgentState) -> tuple[AgentState, RunResult]:
        """执行 Agent"""
        start_time = time()
        tool_calls = []

        # 1. 分析
        await self.hooks.emit("before_analyze", state)
        state = await AnalyzeStep().execute(state, self)
        await self.hooks.emit("after_analyze", state)

        # 2. 路由
        next_step = await self.router.route(state)
        state.step_history.append(f"route:{next_step}")

        # 3. 执行搜索（如果需要）
        if next_step == "search":
            state = await SearchStep().execute(state, self)

        # 4. 摘要
        state = await SummarizeStep().execute(state, self)

        # 5. 评估
        state = await EvaluateStep().execute(state, self)

        return state, RunResult(
            output=state.summary or "",
            steps=state.step_history,
            tool_calls=tool_calls,
            total_duration=time() - start_time,
            token_usage=state.metadata.get("usage", {}),
        )

    async def summarize(self, entry_id: str, content: str) -> dict:
        """主入口"""
        state = AgentState(entry_id=entry_id, content=content)
        state, result = await self.run(state)

        return {
            "entry_id": entry_id,
            "summary_text": state.summary or "",
            "status": "success",
            "provider": self.provider_name,
            "model": self.model_name,
            "steps": result.steps,
            "duration": result.total_duration,
        }


def _provider_name_from_base_url(base_url: str) -> str:
    if not base_url:
        return "custom"

    host = urlparse(base_url).hostname or base_url
    host = host.replace("www.", "")
    parts = host.split(".")
    if len(parts) >= 2:
        return parts[-2]
    return host


def _extract_mock_content(prompt: str) -> str:
    parts = prompt.split("\n\n", 1)
    content = parts[1] if len(parts) > 1 else prompt
    return re.sub(r"\s+", " ", content).strip()


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"
