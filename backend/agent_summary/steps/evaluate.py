"""评估步骤"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from steps.base import BaseStep
from core.state import AgentState
from core.config import EVAL_MIN_LENGTH


class EvaluateStep(BaseStep):
    """评估摘要质量"""
    
    async def execute(self, state: AgentState, agent) -> AgentState:
        # 简单检查：摘要长度是否合理
        if state.summary and len(state.summary) < EVAL_MIN_LENGTH:
            # 太短，重试一次
            from steps.summarize import SummarizeStep
            state = await SummarizeStep().execute(state, agent)
            state.step_history.append("evaluate:retry")
        else:
            state.step_history.append("evaluate:pass")
        return state
