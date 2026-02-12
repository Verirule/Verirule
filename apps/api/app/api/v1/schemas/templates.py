from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

TemplateCadence = Literal["manual", "hourly", "daily", "weekly"]
TemplateSourceKind = Literal["web", "rss", "atom"]


class FrameworkTemplateSourceOut(BaseModel):
    id: UUID
    template_id: UUID
    title: str
    url: str
    kind: TemplateSourceKind
    cadence: TemplateCadence
    tags: list[str]
    enabled_by_default: bool
    created_at: datetime


class FrameworkTemplateOut(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str
    category: str
    is_public: bool
    created_at: datetime
    sources: list[FrameworkTemplateSourceOut] = Field(default_factory=list)


class TemplateApplyOverridesIn(BaseModel):
    cadence: str | None = None
    enable_all: bool | None = None


class TemplateApplyIn(BaseModel):
    org_id: UUID
    template_slug: str = Field(min_length=1, max_length=120)
    overrides: TemplateApplyOverridesIn | None = None


class AppliedSourceOut(BaseModel):
    id: UUID
    name: str
    title: str | None = None
    url: str
    kind: Literal["html", "rss", "pdf", "github_releases"]
    cadence: TemplateCadence
    is_enabled: bool
    tags: list[str] = Field(default_factory=list)


class TemplateApplyOut(BaseModel):
    created: int
    skipped: int
    sources: list[AppliedSourceOut] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
