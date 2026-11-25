"""Code optimization endpoint."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_inference_engine
from app.core.prompts import build_task_prompt
from app.schemas.request import OptimizeRequest
from app.schemas.response import OptimizeResponse
from app.utils.response_formatter import extract_code, extract_sections

router = APIRouter()


@router.post("/optimize", response_model=OptimizeResponse)
def optimize(
    payload: OptimizeRequest,
    engine: Any = Depends(get_inference_engine),
) -> OptimizeResponse:
    """Suggest readable code improvements and complexity estimates."""
    prompt = build_task_prompt(
        "optimization",
        language=payload.programming_language,
        content=payload.code,
        details=payload.optimization_objective,
    )
    raw = engine.generate(
        prompt,
        task_type="optimization",
        language=payload.programming_language,
        generation_options=payload.generation.model_dump(),
    )
    sections = extract_sections(
        raw,
        {
            "code": ("optimized code", "code"),
            "improvements": ("improvements", "explanation of improvements"),
            "time": ("time complexity",),
            "space": ("space complexity",),
        },
    )
    return OptimizeResponse(
        optimized_code=extract_code(sections["code"], raw),
        explanation_of_improvements=sections["improvements"],
        time_complexity=sections["time"] or None,
        space_complexity=sections["space"] or None,
    )
