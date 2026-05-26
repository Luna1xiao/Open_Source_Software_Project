"""HTTP 路由层"""

from fastapi import APIRouter

from ..agent.summary_agent import SummaryAgent

router = APIRouter(prefix="/agents/summary", tags=["agent-summary"])


@router.post("/")
async def summarize(entry_id: str, content: str):
    """摘要单条文章"""
    agent = SummaryAgent()
    result = await agent.summarize(entry_id, content)
    return result


@router.get("/{entry_id}")
async def get_cached(entry_id: str):
    """获取缓存的摘要"""
    # TODO: 实现缓存查询
    return {"entry_id": entry_id, "summary_text": "", "status": "not_found"}
