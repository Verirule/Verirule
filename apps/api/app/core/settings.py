from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    VERIRULE_ENV: str = "development"
    VERIRULE_MODE: str = "api"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_CORS_ORIGINS: str = "http://localhost:3000"
    REQUIRE_ALERT_EVIDENCE_FOR_RESOLVE: bool = True
    ALERT_RESOLVE_MIN_EVIDENCE: int = 1
    SLACK_ALERT_NOTIFICATIONS_ENABLED: bool = True
    VERIRULE_SECRETS_KEY: str | None = None
    INTEGRATIONS_ENCRYPTION_KEY: str | None = None
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_ISSUER: str | None = None
    SUPABASE_JWKS_URL: str | None = None
    WORKER_SUPABASE_ACCESS_TOKEN: str | None = None
    WORKER_POLL_INTERVAL_SECONDS: int = 5
    WORKER_BATCH_LIMIT: int = 5
    WORKER_FETCH_TIMEOUT_SECONDS: float = 10.0
    WORKER_FETCH_MAX_BYTES: int = 1_000_000
    EXPORTS_BUCKET_NAME: str = "exports"
    EXPORT_SIGNED_URL_SECONDS: int = 300

    @model_validator(mode="after")
    def apply_supabase_defaults(self) -> "Settings":
        if not self.SUPABASE_URL.strip():
            raise ValueError("SUPABASE_URL must be configured")
        if not self.SUPABASE_ANON_KEY.strip():
            raise ValueError("SUPABASE_ANON_KEY must be configured")

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
