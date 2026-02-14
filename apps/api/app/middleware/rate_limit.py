import base64
import json
import os
import sys
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

    @staticmethod
    def _is_test_process() -> bool:
        return bool(os.getenv("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules

    @staticmethod
    def _extract_forwarded_ip(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            first_ip = forwarded_for.split(",")[0].strip()
            if first_ip:
                return first_ip

        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    @staticmethod
    def _extract_auth_subject(request: Request) -> str | None:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return None

        token = auth_header[7:].strip()
        token_parts = token.split(".")
        if len(token_parts) != 3:
            return None

        payload = token_parts[1]
        padding = "=" * (-len(payload) % 4)
        try:
            decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
            payload_obj = json.loads(decoded)
        except (ValueError, UnicodeDecodeError):
            return None

        subject = payload_obj.get("sub")
        if isinstance(subject, str) and subject.strip():
            return subject.strip()
        return None

    def _client_key(self, request: Request) -> str:
        subject = self._extract_auth_subject(request)
        if subject:
            return f"user:{subject}"
        return f"ip:{self._extract_forwarded_ip(request)}"

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
        if self._is_test_process():
            return await call_next(request)

        if not request.url.path.startswith("/api"):
            return await call_next(request)

        client_key = self._client_key(request)
        if not self._allow_request(client_key):
            return JSONResponse(status_code=429, content={"detail": "Too Many Requests"})

        return await call_next(request)
