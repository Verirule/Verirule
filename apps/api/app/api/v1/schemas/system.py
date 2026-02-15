from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SystemStatusRowOut(BaseModel):
    id: str
    updated_at: datetime
    payload: dict[str, Any]


class SystemStatusListOut(BaseModel):
    status: list[SystemStatusRowOut]


class SystemHealthOut(BaseModel):
    ok: bool
    version: str
    time_utc: datetime
    supabase_ok: bool


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
