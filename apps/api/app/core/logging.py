from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from app.core.settings import get_settings

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_configured = False

_RESERVED_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}
_SENSITIVE_KEY_FRAGMENTS = ("secret", "token", "password", "apikey", "api_key", "key")


def set_request_id(request_id: str | None) -> Token[str | None]:
    return _request_id_var.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id_var.reset(token)


def get_request_id() -> str | None:
    return _request_id_var.get()


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    return str(value)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "msg": record.getMessage(),
            "component": getattr(record, "component", record.name),
        }

        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id

        for key, value in record.__dict__.items():
            if key in _RESERVED_KEYS or key.startswith("_"):
                continue
            if key in {"message", "asctime", "component", "request_id"}:
                continue
            if _is_sensitive_key(key):
                payload[key] = "[redacted]"
                continue
            payload[key] = _json_safe_value(value)

        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
            payload["error"] = str(record.exc_info[1])[:500] if record.exc_info[1] else "unknown"

        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    level_name = settings.LOG_LEVEL.strip().upper() or "INFO"
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
