"""Code generation endpoint."""

from typing import Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_inference_engine
from app.core.prompts import build_task_prompt
from app.schemas.request import GenerateRequest
from app.schemas.response import GenerateResponse
from app.utils.response_formatter import extract_code, extract_sections

router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
def generate(
    payload: GenerateRequest,
    engine: Any = Depends(get_inference_engine),
) -> GenerateResponse:
    """Generate understandable code and a concise explanation."""
    prompt = build_task_prompt(
        "code_generation",
        language=payload.programming_language,
        content=payload.problem_description,
        details=payload.additional_instructions,
    )
    raw = engine.generate(
        prompt,
        task_type="code_generation",
        language=payload.programming_language,
        generation_options=payload.generation.model_dump(),
    )
    sections = extract_sections(raw, {"code": ("code", "generated code"), "explanation": ("explanation",)})
    return GenerateResponse(
        generated_code=extract_code(sections["code"], raw),
        explanation=sections["explanation"],
    )
