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
    ALLOWED_HOSTS: List[str] = _split_csv(_require("ALLOWED_HOSTS"))
    JWT_ALGORITHM: str = _get_env("JWT_ALGORITHM", "HS256")


def get_settings() -> Settings:
    return Settings()
