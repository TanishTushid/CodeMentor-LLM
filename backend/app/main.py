"""FastAPI application factory and process lifecycle."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from app.api.routes import chat, debug, explain, generate, optimize
from app.config import Settings
from app.core.inference import InferenceError
from app.core.model_loader import ModelLoadError, ModelLoader
from app.schemas.response import HealthResponse

logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware:
    """Reject oversized requests before JSON parsing, including chunked bodies."""

    def __init__(self, app: Any, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            content_length = headers.get(b"content-length")
            if content_length:
                try:
                    too_large = int(content_length) > self.max_bytes
                except ValueError:
                    too_large = False
                if too_large:
                    response = JSONResponse(
                        status_code=413,
                        content={"detail": "Request body is too large."},
                    )
                    await response(scope, receive, send)
                    return

            messages: list[dict[str, Any]] = []
            body_size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                messages.append(message)
                body_size += len(message.get("body", b""))
                if body_size > self.max_bytes:
                    response = JSONResponse(
                        status_code=413,
                        content={"detail": "Request body is too large."},
                    )
                    await response(scope, receive, send)
                    return
                if not message.get("more_body", False):
                    break

            next_message = 0

            async def replay_body() -> dict[str, Any]:
                nonlocal next_message
                if next_message < len(messages):
                    message = messages[next_message]
                    next_message += 1
                    return message
                return await receive()

            await self.app(scope, replay_body, send)
            return
        await self.app(scope, receive, send)


def create_app(
    *,
    settings: Settings | None = None,
    inference_engine: Any | None = None,
) -> FastAPI:
    """Create the API; an injected engine keeps tests independent of model weights."""
    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.inference_engine = inference_engine
        application.state.model_status = "loaded" if inference_engine is not None else "disabled"
        application.state.model_error = None
        if inference_engine is None and app_settings.load_model_on_startup:
            application.state.model_status = "disabled"
            try:
                application.state.inference_engine = ModelLoader(app_settings).load()
                application.state.model_status = "loaded"
            except ModelLoadError:
                logger.exception("Model failed to load during application startup")
                application.state.model_status = "failed"
                application.state.model_error = "Model failed to load; check server logs."
        yield

    application = FastAPI(
        title=app_settings.app_name,
        description="A programming mentor powered by a locally fine-tuned Qwen LoRA adapter.",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.settings = app_settings
    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=app_settings.max_request_bytes,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.exception_handler(InferenceError)
    async def inference_error_handler(
        request: Request,
        exc: InferenceError,
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @application.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred."},
        )

    @application.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        """Report API health and the startup model state."""
        model_status = getattr(application.state, "model_status", "disabled")
        engine = getattr(application.state, "inference_engine", None)
        return HealthResponse(
            status="ok" if model_status == "loaded" else "degraded",
            model_status=model_status,
            device=getattr(engine, "device_name", str(getattr(engine, "device", ""))) or None,
            model_name=app_settings.model_name,
            error=getattr(application.state, "model_error", None),
        )

    for router in (chat.router, generate.router, explain.router, debug.router, optimize.router):
        application.include_router(router, prefix="/api", tags=["coding assistance"])

    # Resolve from this module; keeps static paths independent of the process working directory.
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.is_dir():
        application.mount("/static", StaticFiles(directory=frontend_dir), name="frontend")

        @application.get("/", include_in_schema=False)
        def frontend_index() -> FileResponse:
            return FileResponse(frontend_dir / "index.html")
    return application


app = create_app()
