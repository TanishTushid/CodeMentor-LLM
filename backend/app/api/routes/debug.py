"""Code debugging endpoint."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_inference_engine
from app.core.prompts import build_task_prompt
from app.schemas.request import DebugRequest
from app.schemas.response import DebugResponse
from app.utils.response_formatter import extract_code, extract_sections

router = APIRouter()


@router.post("/debug", response_model=DebugResponse)
def debug(
    payload: DebugRequest,
    engine: Any = Depends(get_inference_engine),
) -> DebugResponse:
    """Diagnose supplied code without executing it."""
    prompt = build_task_prompt(
        "debugging",
        language=payload.programming_language,
        content=payload.code,
        details=payload.error_message,
    )
    raw = engine.generate(
        prompt,
        task_type="debugging",
        language=payload.programming_language,
        generation_options=payload.generation.model_dump(),
    )
    sections = extract_sections(
        raw,
        {
            "issue": ("issue", "identified issue"),
            "code": ("corrected code", "code"),
            "explanation": ("explanation of the fix", "explanation"),
        },
    )
    return DebugResponse(
        identified_issue=sections["issue"],
        corrected_code=extract_code(sections["code"], raw),
        explanation_of_the_fix=sections["explanation"],
    )
