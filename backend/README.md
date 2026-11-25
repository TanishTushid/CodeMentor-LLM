# Backend

The FastAPI application lives in `app/`; it loads the local Qwen LoRA adapter
once at startup and exposes `/api/health`, `/api/chat`, `/api/generate`,
`/api/explain`, `/api/debug`, and `/api/optimize`.

From the repository root, see the root [README](../README.md) for adapter and
hardware details, environment configuration, installation, Swagger UI, and API
test commands. Start the server with:

```powershell
uv run uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
