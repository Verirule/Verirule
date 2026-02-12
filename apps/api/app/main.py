from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware

configure_logging()
settings = get_settings()

app = FastAPI(title="Verirule API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RateLimitMiddleware, max_requests_per_minute=60)
app.add_middleware(RequestIDMiddleware)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/healthz")
def root_healthz() -> dict[str, str]:
    return {"status": "ok"}
