"""General programming chat endpoint."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_inference_engine
from app.schemas.request import ChatRequest
from app.schemas.response import ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    engine: Any = Depends(get_inference_engine),
) -> ChatResponse:
    """Answer a programming question while incorporating optional history."""
    response = engine.generate(
        payload.message,
        task_type="general",
        history=[message.model_dump() for message in payload.conversation_history],
        generation_options=payload.generation.model_dump(),
    )
    return ChatResponse(response=response, task_type="general")
