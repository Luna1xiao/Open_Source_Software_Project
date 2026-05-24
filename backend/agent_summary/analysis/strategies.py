"""摘要策略"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.state import ArticleProfile
from core.config import DIRECT_THRESHOLD, SINGLE_PASS_THRESHOLD


def select_strategy(profile: ArticleProfile) -> str:
    """根据文章特征选择摘要策略"""
    if profile.length < DIRECT_THRESHOLD:
        return "direct"
    elif profile.length < SINGLE_PASS_THRESHOLD:
        return "single_pass"
    else:
        return "hierarchical"
