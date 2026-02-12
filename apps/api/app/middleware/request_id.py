import uuid
from time import perf_counter

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, reset_request_id, set_request_id

logger = get_logger("api.request")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a stable request ID to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        request_id_token = set_request_id(request_id)
        started = perf_counter()
        response: Response | None = None

        logger.info(
            "request.start",
            extra={
                "component": "api",
                "method": request.method,
                "path": request.url.path,
            },
        )
        try:
            response = await call_next(request)
            return response
        except Exception:
            logger.exception(
                "request.error",
                extra={
                    "component": "api",
                    "method": request.method,
                    "path": request.url.path,
                },
            )
            raise
        finally:
            duration_ms = int((perf_counter() - started) * 1000)
            status_code = response.status_code if response is not None else 500
            logger.info(
                "request.end",
                extra={
                    "component": "api",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            reset_request_id(request_id_token)
