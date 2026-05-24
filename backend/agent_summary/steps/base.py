"""步骤基类"""

from abc import ABC, abstractmethod
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.state import AgentState


class BaseStep(ABC):
    """步骤基类"""
    
    @abstractmethod
    async def execute(self, state: AgentState, agent) -> AgentState:
        """执行步骤"""
        ...
