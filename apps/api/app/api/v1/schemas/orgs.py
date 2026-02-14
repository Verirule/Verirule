from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrgOut(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class OrgCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=64)
