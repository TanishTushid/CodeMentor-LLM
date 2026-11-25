"""Code explanation endpoint."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_inference_engine
from app.core.prompts import build_task_prompt
from app.schemas.request import ExplainRequest
from app.schemas.response import ExplainResponse
from app.utils.response_formatter import extract_sections, split_bullets

router = APIRouter()


@router.post("/explain", response_model=ExplainResponse)
def explain(
    payload: ExplainRequest,
    engine: Any = Depends(get_inference_engine),
) -> ExplainResponse:
    """Explain supplied code at the requested learner level."""
    prompt = build_task_prompt(
        "code_explanation",
        language=payload.programming_language,
        content=payload.code,
        details=payload.explanation_level,
    )
    raw = engine.generate(
        prompt,
        task_type="code_explanation",
        language=payload.programming_language,
        generation_options=payload.generation.model_dump(),
    )
    sections = extract_sections(
        raw,
        {
            "explanation": ("explanation",),
            "concepts": ("important concepts", "concepts"),
            "steps": ("step-by-step breakdown", "steps", "breakdown"),
        },
    )
    return ExplainResponse(
        code_explanation=sections["explanation"] or raw,
        important_concepts=split_bullets(sections["concepts"]),
        step_by_step_breakdown=split_bullets(sections["steps"]),
    )
