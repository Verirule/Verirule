from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SourceOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    type: Literal["rss", "url"]
    url: str
    is_enabled: bool
    cadence: Literal["manual", "hourly", "daily", "weekly"] = "manual"
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    created_at: datetime


class SourceCreateIn(BaseModel):
    org_id: UUID
    name: str = Field(min_length=1, max_length=120)
    type: Literal["rss", "url"]
    url: str = Field(min_length=1, max_length=2048)


class SourceToggleIn(BaseModel):
    is_enabled: bool


class SourceScheduleIn(BaseModel):
    cadence: Literal["manual", "hourly", "daily", "weekly"]
