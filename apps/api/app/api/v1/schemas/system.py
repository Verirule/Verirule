from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class SystemStatusRowOut(BaseModel):
    id: str
    updated_at: datetime
    payload: dict[str, Any]


class SystemStatusListOut(BaseModel):
    status: list[SystemStatusRowOut]


class SystemHealthOut(BaseModel):
    api: Literal["ok"]
    worker: Literal["ok", "stale", "unknown"]
    worker_last_seen_at: datetime | None = None
    stale_after_seconds: int
