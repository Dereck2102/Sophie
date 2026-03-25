from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "SOPHIE ERP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Observability
    METRICS_ENABLED: bool = os.getenv("METRICS_ENABLED", "true").lower() in {"1", "true", "yes"}
    METRICS_PATH: str = os.getenv("METRICS_PATH", "/metrics")

    # Module rollout flags
    ENABLE_CRM_MODULE: bool = os.getenv("ENABLE_CRM_MODULE", "true").lower() in {"1", "true", "yes"}
    ENABLE_CAJA_CHICA_MODULE: bool = os.getenv("ENABLE_CAJA_CHICA_MODULE", "true").lower() in {"1", "true", "yes"}

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sophie_user:sophie_pass@localhost:5432/sophie_db"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-32chars!!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    MFA_EMAIL_CODE_EXPIRE_MINUTES: int = 10
    SECURITY_HEADERS_ENABLED: bool = os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() in {"1", "true", "yes"}
    TRUSTED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "testserver",
        "test",
        "backend",
        "frontend",
        "nginx",
        "prometheus",
        "sophie-backend",
        "sophie-frontend",
        "sophie-nginx",
        "sophie-prometheus",
    ]
    REQUEST_BODY_MAX_BYTES: int = int(os.getenv("REQUEST_BODY_MAX_BYTES", "1048576"))
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in {"1", "true", "yes"}
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "240"))
    RATE_LIMIT_AUTH_MAX_REQUESTS: int = int(os.getenv("RATE_LIMIT_AUTH_MAX_REQUESTS", "120"))
    GZIP_ENABLED: bool = os.getenv("GZIP_ENABLED", "true").lower() in {"1", "true", "yes"}
    GZIP_MINIMUM_SIZE: int = int(os.getenv("GZIP_MINIMUM_SIZE", "1024"))

    # SMTP / email delivery
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "no-reply@sophie.local")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "SOPHIE")

    # SMS delivery (Twilio)
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_PHONE: str = os.getenv("TWILIO_FROM_PHONE", "")  # e.g. '+15017250604'

    # MFA / 2FA
    MFA_ISSUER: str = "SOPHIE - Big Solutions"
    MFA_EMAIL_DEBUG_FALLBACK: bool = os.getenv("MFA_EMAIL_DEBUG_FALLBACK", "true").lower() in {"1", "true", "yes"}
    # Set TWOFA_ENABLED=false to bypass all 2FA globally (e.g. during initial setup)
    TWOFA_ENABLED: bool = os.getenv("TWOFA_ENABLED", "true").lower() in {"1", "true", "yes"}
    OWNER_SUPERADMIN_USERNAME: str = os.getenv("OWNER_SUPERADMIN_USERNAME", "damacoria")

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
