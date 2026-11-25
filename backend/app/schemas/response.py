"""Typed API response models."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """API readiness and model status."""

    status: Literal["ok", "degraded"]
    model_status: Literal["loaded", "failed", "disabled"]
    device: str | None
    model_name: str
    error: str | None = None


class ChatResponse(BaseModel):
    """General chat response."""

    response: str
    task_type: str


class GenerateResponse(BaseModel):
    """Structured code generation response."""

    generated_code: str
    explanation: str


class ExplainResponse(BaseModel):
    """Structured code explanation response."""

    code_explanation: str
    important_concepts: list[str]
    step_by_step_breakdown: list[str]


class DebugResponse(BaseModel):
    """Structured debugging response."""

    identified_issue: str
    corrected_code: str
    explanation_of_the_fix: str


class OptimizeResponse(BaseModel):
    """Structured optimization response."""

    optimized_code: str
    explanation_of_improvements: str
    time_complexity: str | None
    space_complexity: str | None
