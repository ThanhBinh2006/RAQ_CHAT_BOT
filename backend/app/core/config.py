"""
Application configuration loaded from environment variables.
Supports .env file via pydantic-settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/raq_chatbot"

    # ── MinIO S3 Storage ─────────────────────────────────────
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "pdf-storage"
    MINIO_USE_SSL: bool = False

    # ── JWT Authentication ───────────────────────────────────
    JWT_SECRET_KEY: str = "your_super_secret_jwt_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── System Cloud API Keys ────────────────────────────────
    SYSTEM_DEFAULT_API_KEY: Optional[str] = None
    SYSTEM_DEFAULT_EMBEDDING_KEY: Optional[str] = None
    SYSTEM_DEFAULT_API_BASE: str = "https://integrate.api.nvidia.com/v1"
    SYSTEM_PROVIDER: Optional[str] = None

    # ── Default Models ───────────────────────────────────────
    DEFAULT_CHAT_MODEL: str
    DEFAULT_EMBEDDING_MODEL: str
    # ── Mock Mode ────────────────────────────────────────────
    USE_MOCK_LLM: bool = True

    # ── CORS ─────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
