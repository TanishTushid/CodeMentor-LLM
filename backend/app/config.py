"""Environment-backed application settings."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Settings shared by the API, model loader, and inference engine."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Code Mentor AI"
    model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    adapter_path: Path = PROJECT_ROOT / "code_mentor_model" / "code_mentor_lora_model"
    device: str = "auto"
    load_model_on_startup: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    max_request_bytes: int = 65_536
    max_input_tokens: int = 4096

    @field_validator("adapter_path", mode="before")
    @classmethod
    def resolve_adapter_path(cls, value: str | Path) -> Path:
        """Resolve relative adapter paths against the repository root."""
        path = Path(value)
        return path if path.is_absolute() else PROJECT_ROOT / path

    @property
    def allowed_origins(self) -> list[str]:
        """Return configured CORS origins, excluding empty entries."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
