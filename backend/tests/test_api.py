"""API contract tests that do not load model weights."""

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.model_loader import ModelLoadError
from app.main import RequestSizeLimitMiddleware, create_app


class FakeInferenceEngine:
    """Small deterministic engine for endpoint contract tests."""

    device_name = "cpu"

    def generate(
        self,
        prompt: str,
        *,
        task_type: str,
        language: str | None = None,
        history: Sequence[Mapping[str, str]] | None = None,
        generation_options: Mapping[str, Any] | None = None,
    ) -> str:
        outputs = {
            "general": "A concise programming explanation.",
            "code_generation": "## Code\n```python\nprint('hi')\n```\n## Explanation\nPrints a greeting.",
            "code_explanation": (
                "## Explanation\nPrints a greeting.\n## Important Concepts\n- Function call"
                "\n## Step-by-step Breakdown\n1. Call print"
            ),
            "debugging": (
                "## Issue\nMissing closing parenthesis.\n## Corrected Code\n"
                "```python\nprint('hi')\n```\n## Explanation of the Fix\nClosed the call."
            ),
            "optimization": (
                "## Optimized Code\n```python\nprint('hi')\n```\n## Improvements\n"
                "No unnecessary work.\n## Time Complexity\nO(1)\n## Space Complexity\nO(1)"
            ),
        }
        return outputs[task_type]


@pytest.fixture
def client() -> TestClient:
    """Return an app whose lifespan uses a fake inference engine."""
    app = create_app(inference_engine=FakeInferenceEngine())
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_loaded_test_model(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["model_status"] == "loaded"
    assert response.json()["device"] == "cpu"
    assert response.json()["model_name"] == "Qwen/Qwen2.5-0.5B-Instruct"


def test_swagger_documentation_is_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    openapi = client.get("/openapi.json").json()
    assert "/api/generate" in openapi["paths"]


@pytest.mark.parametrize(
    ("path", "payload", "expected"),
    [
        ("/api/chat", {"message": "What is a loop?"}, "response"),
        (
            "/api/generate",
            {"programming_language": "Python", "problem_description": "Print hi"},
            "generated_code",
        ),
        (
            "/api/explain",
            {"code": "print('hi')", "programming_language": "Python"},
            "code_explanation",
        ),
        (
            "/api/debug",
            {"code": "print('hi'", "programming_language": "Python"},
            "corrected_code",
        ),
        (
            "/api/optimize",
            {"code": "print('hi')", "programming_language": "Python"},
            "optimized_code",
        ),
    ],
)
def test_coding_endpoints_return_expected_fields(
    client: TestClient,
    path: str,
    payload: dict[str, str],
    expected: str,
) -> None:
    response = client.post(path, json=payload)
    assert response.status_code == 200
    assert expected in response.json()


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/chat", {}),
        ("/api/generate", {"programming_language": "Python"}),
        ("/api/explain", {"programming_language": "Python"}),
        ("/api/debug", {"code": "print(1)"}),
        ("/api/optimize", {"code": "print(1)"}),
    ],
)
def test_missing_required_inputs_return_422(
    client: TestClient,
    path: str,
    payload: dict[str, str],
) -> None:
    response = client.post(path, json=payload)
    assert response.status_code == 422


def test_invalid_generation_options_return_422(client: TestClient) -> None:
    response = client.post(
        "/api/chat",
        json={"message": "Explain recursion", "generation": {"max_new_tokens": 0}},
    )
    assert response.status_code == 422


def test_health_reports_model_load_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_load(self: Any) -> Any:
        raise ModelLoadError("test failure")

    monkeypatch.setattr("app.main.ModelLoader.load", fail_load)
    app = create_app(settings=Settings(load_model_on_startup=True))
    with TestClient(app) as test_client:
        response = test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert response.json()["model_status"] == "failed"
        assert "test failure" not in response.text
        assert test_client.post("/api/chat", json={"message": "Hi"}).status_code == 503


def test_request_size_limit_returns_413() -> None:
    app = create_app(
        settings=Settings(max_request_bytes=32),
        inference_engine=FakeInferenceEngine(),
    )
    with TestClient(app) as test_client:
        response = test_client.post("/api/chat", json={"message": "x" * 100})
        assert response.status_code == 413


def test_chunked_request_size_limit_returns_413() -> None:
    messages = iter(
        [
            {"type": "http.request", "body": b"123456", "more_body": True},
            {"type": "http.request", "body": b"789", "more_body": False},
        ]
    )
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return next(messages)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    middleware = RequestSizeLimitMiddleware(lambda *_: None, max_bytes=8)
    asyncio.run(middleware({"type": "http", "headers": []}, receive, send))

    assert sent[0]["status"] == 413
