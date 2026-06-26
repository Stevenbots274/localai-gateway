"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = Field(default="LocalAI Gateway")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")

    # Server
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")

    # Database (Neon)
    DATABASE_URL: str = Field(default="")
    DATABASE_URL_SYNC: str = Field(default="")

    # Security
    SECRET_KEY: str = Field(default="change-me-in-production-min-32-chars-long")
    API_KEY_HEADER: str = Field(default="X-API-Key")
    ADMIN_API_KEY: str = Field(default="admin-change-me-immediately")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # LocalAI
    LOCALAI_URL: str = Field(default="http://localhost:8080")
    LOCALAI_API_KEY: str = Field(default="")

    # CORS
    CORS_ORIGINS: str = Field(default="*")

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_BURST: int = Field(default=10)

    # File Upload
    MAX_UPLOAD_SIZE: int = Field(default=104857600)

    # Cache
    CACHE_TTL_SECONDS: int = Field(default=300)

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def localai_base_url(self) -> str:
        return self.LOCALAI_URL.rstrip("/")

    @property
    def localai_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.LOCALAI_API_KEY:
            headers["Authorization"] = f"Bearer {self.LOCALAI_API_KEY}"
        return headers

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
