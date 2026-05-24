"""测试 Agent 层"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.summary_agent import SummaryAgent, MockLLM
from core.state import AgentState, ArticleProfile


class TestSummaryAgent:
    """测试 SummaryAgent"""
    
    @pytest.mark.asyncio
    async def test_run_returns_state_and_result(self, short_article):
        agent = SummaryAgent()
        state = AgentState(entry_id="test-1", content=short_article)
        
        state, result = await agent.run(state)
        
        assert state.summary is not None
        assert len(state.summary) > 0
        assert result.output == state.summary
        assert len(result.steps) > 0
    
    @pytest.mark.asyncio
    async def test_run_records_steps(self, short_article):
        agent = SummaryAgent()
        state = AgentState(entry_id="test-2", content=short_article)
        
        state, result = await agent.run(state)
        
        assert "analyze" in state.step_history
        assert any(s.startswith("route:") for s in state.step_history)
        assert any(s.startswith("summarize:") for s in state.step_history)
        assert any(s.startswith("evaluate:") for s in state.step_history)
    
    @pytest.mark.asyncio
    async def test_summarize_returns_result(self, short_article):
        agent = SummaryAgent()
        result = await agent.summarize("test-3", short_article)
        
        assert result["entry_id"] == "test-3"
        assert result["status"] == "success"
        assert len(result["summary_text"]) > 0
        assert result["duration"] > 0
    
    @pytest.mark.asyncio
    async def test_long_article_uses_correct_strategy(self, long_article):
        """测试长文章使用正确的策略"""
        agent = SummaryAgent()
        state = AgentState(entry_id="test-4", content=long_article)
        
        state, result = await agent.run(state)
        
        # 根据文章长度判断应该使用的策略
        if len(long_article) > 8000:
            assert "hierarchical" in " ".join(state.step_history)
        else:
            assert "direct" in " ".join(state.step_history)
        
        assert state.summary is not None
    
    @pytest.mark.asyncio
    async def test_mock_llm(self):
        llm = MockLLM()
        response = await llm.chat("Test prompt")
        assert "Mock summary" in response
