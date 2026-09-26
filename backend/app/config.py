# -*- coding: utf-8 -*-
"""
backend/app/config.py

Centralised configuration using python-dotenv.

WHY THIS PATTERN?
-----------------
Instead of sprinkling os.getenv() calls throughout the codebase,
we load all environment variables in ONE place. Every other module
imports `settings` from here. This ensures:
  - Clear specification of all required environment variables
  - Environment-based validation (e.g. rejecting wildcard CORS in production)
  - Safe fallbacks for local development
"""

import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()


def _normalize_db_url(url: str) -> str:
    """Normalize and safely URL-encode DATABASE_URL for SQLAlchemy."""
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if "://" in url:
        prefix, rest = url.split("://", 1)
        if "@" in rest:
            last_at = rest.rfind("@")
            creds = rest[:last_at]
            host_part = rest[last_at + 1 :]
            if ":" in creds:
                user, password = creds.split(":", 1)
                clean_pw = urllib.parse.quote_plus(urllib.parse.unquote_plus(password))
                url = f"{prefix}://{user}:{clean_pw}@{host_part}"
    return url


class Settings:
    """Application settings loaded from environment variables."""

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").strip().lower()
    DEBUG: bool = os.getenv("DEBUG", "false").strip().lower() == "true"

    # Database
    DATABASE_URL: str = _normalize_db_url(
        os.getenv(
            "DATABASE_URL",
            "sqlite:///backend/journeyiq.db",
        )
    )
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))

    # API metadata
    APP_NAME: str = "JourneyIQ API"
    APP_VERSION: str = "0.1.0"

    # CORS
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    ).strip()

    # Trusted Hosts
    ALLOWED_HOSTS: str = os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,testserver",
    ).strip()

    @property
    def cors_origins_list(self) -> list[str]:
        """
        Return parsed list of allowed CORS origins.
        Enforces that production environments cannot use wildcard '*'.
        """
        raw = self.CORS_ORIGINS
        if not raw:
            return []
        origins = [orig.strip() for orig in raw.split(",") if orig.strip()]
        if self.ENVIRONMENT == "production" and "*" in origins:
            raise ValueError(
                "Insecure configuration: wildcard CORS origin ('*') is strictly disallowed in production."
            )
        return origins

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Return parsed list of allowed Host header values."""
        raw = self.ALLOWED_HOSTS
        if not raw or raw == "*":
            return ["*"]
        return [host.strip() for host in raw.split(",") if host.strip()]


# Single instance — import this everywhere
settings = Settings()
