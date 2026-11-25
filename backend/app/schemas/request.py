"""Validated API request models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictRequest(BaseModel):
    """Reject unexpected request fields rather than silently ignoring them."""

    model_config = ConfigDict(extra="forbid")


class GenerationOptions(StrictRequest):
    """Validated Transformers generation settings."""

    max_new_tokens: int = Field(default=512, ge=1, le=2048)
    temperature: float = Field(default=0.7, gt=0, le=2)
    top_p: float = Field(default=0.9, gt=0, le=1)
    do_sample: bool = False
    repetition_penalty: float = Field(default=1.05, ge=1, le=2)


class ConversationMessage(StrictRequest):
    """One user or assistant message in chat history."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10_000)


class ChatRequest(StrictRequest):
    """General programming assistance request."""

    message: str = Field(min_length=1, max_length=10_000)
    conversation_history: list[ConversationMessage] = Field(default_factory=list, max_length=20)
    generation: GenerationOptions = Field(default_factory=GenerationOptions)


class GenerateRequest(StrictRequest):
    """Code generation request."""

    programming_language: str = Field(min_length=1, max_length=64)
    problem_description: str = Field(min_length=1, max_length=8_000)
    additional_instructions: str | None = Field(default=None, max_length=4_000)
    generation: GenerationOptions = Field(default_factory=GenerationOptions)


class ExplainRequest(StrictRequest):
    """Code explanation request."""

    code: str = Field(min_length=1, max_length=12_000)
    programming_language: str = Field(min_length=1, max_length=64)
    explanation_level: Literal["beginner", "intermediate", "advanced"] = "beginner"
    generation: GenerationOptions = Field(default_factory=GenerationOptions)


class DebugRequest(StrictRequest):
    """Code debugging request."""

    code: str = Field(min_length=1, max_length=12_000)
    programming_language: str = Field(min_length=1, max_length=64)
    error_message: str | None = Field(default=None, max_length=4_000)
    generation: GenerationOptions = Field(default_factory=GenerationOptions)


class OptimizeRequest(StrictRequest):
    """Code optimization request."""

    code: str = Field(min_length=1, max_length=12_000)
    programming_language: str = Field(min_length=1, max_length=64)
    optimization_objective: str = Field(default="Improve clarity and efficiency", max_length=512)
    generation: GenerationOptions = Field(default_factory=GenerationOptions)
