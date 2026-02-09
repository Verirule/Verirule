from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    VERIRULE_ENV: str = "development"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_CORS_ORIGINS: str = "http://localhost:3000"
    SUPABASE_URL: str
    SUPABASE_ISSUER: str | None = None
    SUPABASE_JWKS_URL: str | None = None

    @model_validator(mode="after")
    def apply_supabase_defaults(self) -> "Settings":
        if not self.SUPABASE_URL.strip():
            raise ValueError("SUPABASE_URL must be configured")

        if not self.SUPABASE_ISSUER:
            self.SUPABASE_ISSUER = f"{self.SUPABASE_URL.rstrip('/')}/auth/v1"
        if not self.SUPABASE_JWKS_URL:
            self.SUPABASE_JWKS_URL = (
                f"{self.SUPABASE_ISSUER.rstrip('/')}/.well-known/jwks.json"
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.API_CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
