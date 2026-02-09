import time
from dataclasses import dataclass
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory per-IP token bucket limiter for /api routes."""

    def __init__(self, app, max_requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.capacity = float(max_requests_per_minute)
        self.refill_rate = self.capacity / 60.0
        self._buckets: dict[str, _Bucket] = {}
        self._lock = Lock()

    def _allow_request(self, client_ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(client_ip)
            if bucket is None:
                bucket = _Bucket(tokens=self.capacity, last_refill=now)

            elapsed = max(0.0, now - bucket.last_refill)
            bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_rate)
            bucket.last_refill = now

            if bucket.tokens < 1:
                self._buckets[client_ip] = bucket
                return False

            bucket.tokens -= 1
            self._buckets[client_ip] = bucket
            return True

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not self._allow_request(client_ip):
            return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})

        return await call_next(request)
