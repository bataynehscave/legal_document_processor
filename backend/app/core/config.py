from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "Legal Document Processing Pipeline"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./contracts.db"

    # LLM Settings
    LLM_PROVIDER: Literal["gemini", "openai"] = "gemini"

    # Gemini Settings (Default: Gemini 3.7 Flash)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.7-flash"

    # OpenAI Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Resilience & Timeouts
    LLM_MAX_RETRIES: int = Field(default=3, ge=1, le=10)
    LLM_RETRY_MIN_WAIT: float = Field(default=1.0, ge=0.1)
    LLM_RETRY_MAX_WAIT: float = Field(default=10.0, ge=1.0)
    LLM_TIMEOUT_SECONDS: float = Field(default=30.0, ge=5.0)
    MAX_PAYLOAD_CHARS: int = Field(default=50000, ge=100)
    MAX_PAYLOAD_BYTES: int = Field(default=200_000, ge=1024)  # 200KB guard

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, ge=1)

    # Async Queue Workers
    QUEUE_MAX_CONCURRENCY: int = Field(default=2, ge=1, le=10)

    # CORS
    FRONTEND_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.FRONTEND_CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
