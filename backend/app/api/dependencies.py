"""Request-scoped dependencies for the API."""

from typing import Any

from fastapi import HTTPException, Request, status


def get_inference_engine(request: Request) -> Any:
    """Return the startup-loaded inference engine or report model unavailability."""
    engine = getattr(request.app.state, "inference_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The model is not available.",
        )
    return engine
