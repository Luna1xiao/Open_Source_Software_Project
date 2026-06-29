"""HTTP routes for summary agent requests."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.schemas.agent import SummaryRequest, SummaryResult

from ..llm_client import LLMClientError
from ..service import (
    ArticleContentUnavailableError,
    ArticleNotFoundError,
    SummaryService,
)

logger = logging.getLogger(__name__)

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


@router.post("/stream")
async def generate_summary_stream(request: SummaryRequest) -> StreamingResponse:
    service = get_summary_service()

    try:
        stream = service.stream_generate(request)
        first_event = await stream.__anext__()

        async def event_stream():
            first_payload = json.dumps(first_event, ensure_ascii=False)
            yield f"event: {first_event.get('type', 'message')}\ndata: {first_payload}\n\n"
            async for event in stream:
                event_type = event.get("type", "message")
                payload = json.dumps(event, ensure_ascii=False)
                yield f"event: {event_type}\ndata: {payload}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except ArticleNotFoundError as exc:
        logger.warning("Streaming summary request for missing article: %s", request.entry_id)
        raise HTTPException(status_code=404, detail="Entry not found") from exc
    except ArticleContentUnavailableError as exc:
        logger.warning(
            "Streaming summary request for article without content: %s",
            request.entry_id,
        )
        raise HTTPException(status_code=409, detail="Entry has no summary content") from exc
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail=exc.detail) from exc
