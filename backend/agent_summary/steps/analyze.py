"""分析步骤"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from steps.base import BaseStep
from core.state import AgentState
from analysis.analyzer import analyze


class AnalyzeStep(BaseStep):
    """分析文章"""
    
    async def execute(self, state: AgentState, agent) -> AgentState:
        state.profile = analyze(state.content)
        state.step_history.append("analyze")
        return state
