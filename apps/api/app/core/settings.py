from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    VERIRULE_ENV: str = "development"
    VERIRULE_MODE: str = "api"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    API_CORS_ORIGINS: str = "http://localhost:3000"
    API_RATE_LIMIT_ENABLED: bool = True
    API_RATE_LIMIT_PER_MINUTE: int = 60
    REQUIRE_ALERT_EVIDENCE_FOR_RESOLVE: bool = True
    ALERT_RESOLVE_MIN_EVIDENCE: int = 1
    SLACK_ALERT_NOTIFICATIONS_ENABLED: bool = True
    VERIRULE_SECRETS_KEY: str | None = None
    INTEGRATIONS_ENCRYPTION_KEY: str | None = None
    NEXT_PUBLIC_SITE_URL: str = "https://www.verirule.com"
    EMAIL_FROM: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    DIGEST_SEND_HOUR_UTC: int = 8
    DIGEST_BATCH_LIMIT: int = 50
    NOTIFY_JOB_BATCH_LIMIT: int = 50
    NOTIFY_MAX_ATTEMPTS: int = 5
    DIGEST_PROCESSOR_INTERVAL_SECONDS: int = 300
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_ISSUER: str | None = None
    SUPABASE_JWKS_URL: str | None = None
    WORKER_SUPABASE_ACCESS_TOKEN: str | None = None
    WORKER_POLL_INTERVAL_SECONDS: int = 5
    WORKER_BATCH_LIMIT: int = 5
    READINESS_COMPUTE_INTERVAL_SECONDS: int = 900
    WORKER_FETCH_TIMEOUT_SECONDS: float = 10.0
    WORKER_FETCH_MAX_BYTES: int = 1_000_000
    EXPORTS_BUCKET_NAME: str = "exports"
    EXPORT_SIGNED_URL_SECONDS: int = 300
    EVIDENCE_BUCKET_NAME: str = "evidence"
    EVIDENCE_SIGNED_URL_SECONDS: int = 900
    MAX_EVIDENCE_UPLOAD_BYTES: int = 25_000_000
    AUDIT_PACKET_MAX_EVIDENCE_FILES: int = 200
    AUDIT_PACKET_MAX_TOTAL_BYTES: int = 52_428_800
    AUDIT_PACKET_MAX_FILE_BYTES: int = 10_485_760
    WORKER_STALE_AFTER_SECONDS: int = 180

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
        if self.VERIRULE_ENV.strip().lower() == "production":
            if not (self.EMAIL_FROM or "").strip():
                raise ValueError("EMAIL_FROM must be configured in production")
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.API_CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
