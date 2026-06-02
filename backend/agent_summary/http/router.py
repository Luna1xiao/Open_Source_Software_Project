"""HTTP routes for summary agent requests."""

from fastapi import APIRouter, HTTPException

from app.schemas.agent import SummaryRequest, SummaryResult

from ..llm_client import LLMClientError
from ..service import (
    ArticleContentUnavailableError,
    ArticleNotFoundError,
    SummaryService,
)

router = APIRouter(prefix="/agents/summary", tags=["agent-summary"])


def get_summary_service() -> SummaryService:
    return SummaryService()


@router.post("/generate", response_model=SummaryResult)
async def generate_summary(request: SummaryRequest) -> SummaryResult:
    service = get_summary_service()
    try:
        return await service.generate(request)
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Entry not found") from exc
    except ArticleContentUnavailableError as exc:
        raise HTTPException(status_code=409, detail="Entry has no summary content") from exc
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail=exc.detail) from exc
