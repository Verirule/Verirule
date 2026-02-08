import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

# Load .env without overriding existing environment variables
load_dotenv(override=False)


def _get_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value if value is not None else default


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    SECRET_KEY: str = _require("SECRET_KEY")
    DATABASE_URL: str = _require("DATABASE_URL")
    SUPABASE_URL: str = _require("SUPABASE_URL")
    SUPABASE_API_KEY: str = _require("SUPABASE_API_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str = _require("SUPABASE_SERVICE_ROLE_KEY")
    SUPABASE_JWT_SECRET: str = _require("SUPABASE_JWT_SECRET")
    ALLOWED_HOSTS: List[str] = _split_csv(_require("ALLOWED_HOSTS"))
    JWT_ALGORITHM: str = _get_env("JWT_ALGORITHM", "HS256")
    INGESTION_FEED_URL: str = _require("INGESTION_FEED_URL")
    EMAIL_PROVIDER: str = _get_env("EMAIL_PROVIDER", "")
    SMTP_HOST: str = _get_env("SMTP_HOST", "")
    SMTP_PORT: int = int(_get_env("SMTP_PORT", "0") or 0)
    SMTP_USER: str = _get_env("SMTP_USER", "")
    SMTP_PASSWORD: str = _get_env("SMTP_PASSWORD", "")
    SMTP_FROM: str = _get_env("SMTP_FROM", "")
    DASHBOARD_URL: str = _get_env("DASHBOARD_URL", "")
    ALERTS_MAX_PER_RUN: int = int(_get_env("ALERTS_MAX_PER_RUN", "100") or 100)
    RATE_LIMIT_WINDOW_SECONDS: int = int(_get_env("RATE_LIMIT_WINDOW_SECONDS", "60") or 60)
    RATE_LIMIT_MAX_REQUESTS: int = int(_get_env("RATE_LIMIT_MAX_REQUESTS", "120") or 120)


def get_settings() -> Settings:
    return Settings()
