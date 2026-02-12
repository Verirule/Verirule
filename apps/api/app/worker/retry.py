from __future__ import annotations

import re

from fastapi import HTTPException

_BACKOFF_SECONDS = [60, 300, 900, 3600, 21600]
_MAX_ERROR_LENGTH = 500
_SENSITIVE_PATTERNS = (
    re.compile(r"bearer\s+[a-z0-9\-_\.]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
)


def backoff_seconds(attempt: int) -> int:
    if attempt <= 1:
        return _BACKOFF_SECONDS[0]
    if attempt >= len(_BACKOFF_SECONDS):
        return _BACKOFF_SECONDS[-1]
    return _BACKOFF_SECONDS[attempt - 1]


def sanitize_error(exc: Exception, *, default_message: str) -> str:
    if isinstance(exc, HTTPException) and isinstance(exc.detail, str) and exc.detail.strip():
        message = exc.detail.strip()
    else:
        message = str(exc).strip()
    if not message:
        message = default_message

    sanitized = message
    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return sanitized[:_MAX_ERROR_LENGTH]
