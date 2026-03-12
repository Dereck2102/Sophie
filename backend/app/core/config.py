from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SOPHIE ERP/CRM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sophie_user:sophie_pass@localhost:5432/sophie_db"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-32chars!!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # MFA
    MFA_ISSUER: str = "SOPHIE - Big Solutions"

    # Vault encryption (AES-256-GCM key must be 32 bytes base64-encoded)
    VAULT_SECRET_KEY: str = os.getenv("VAULT_SECRET_KEY", "")

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
