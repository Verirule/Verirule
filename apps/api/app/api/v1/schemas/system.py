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


class SystemJobRowOut(BaseModel):
    id: str
    org_id: str
    type: str
    status: str
    attempts: int
    last_error: str | None = None
    updated_at: datetime | None = None


class SystemJobsListOut(BaseModel):
    jobs: list[SystemJobRowOut]
