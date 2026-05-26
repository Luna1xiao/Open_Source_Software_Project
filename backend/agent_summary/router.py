"""HTTP 路由层"""

from fastapi import APIRouter
from pydantic import BaseModel

from .agent.summary_agent import SummaryAgent

router = APIRouter(prefix="/agents/summary", tags=["agent-summary"])


class SummaryRequest(BaseModel):
    entry_id: str
    target_lang: str = "en"


class SummaryResponse(BaseModel):
    entry_id: str
    summary: str


@router.post("/generate", response_model=SummaryResponse)
async def generate_summary(req: SummaryRequest):
    """生成摘要"""
    agent = SummaryAgent()
    result = await agent.summarize(req.entry_id, req.target_lang)
    return SummaryResponse(
        entry_id=result["entry_id"],
        summary=result["summary_text"],
    )
