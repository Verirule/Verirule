from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

TemplateCadence = Literal["manual", "hourly", "daily", "weekly"]


class TemplateListItemOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    default_cadence: TemplateCadence
    tags: list[str]
    source_count: int
    created_at: datetime


class TemplateSourceOut(BaseModel):
    id: UUID
    template_id: UUID
    name: str
    url: str
    cadence: TemplateCadence
    tags: list[str]
    created_at: datetime


class TemplateInstallIn(BaseModel):
    org_id: UUID
