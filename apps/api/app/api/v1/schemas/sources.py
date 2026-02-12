from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

SourceKind = Literal["html", "rss", "pdf", "github_releases"]
LegacySourceType = Literal["rss", "url"]


def _validate_kind_config(kind: SourceKind, config: dict[str, Any]) -> None:
    if kind != "github_releases":
        return

    repo = config.get("repo")
    if not isinstance(repo, str) or "/" not in repo or not repo.strip():
        raise ValueError("github_releases sources require config.repo in owner/name format")


class SourceOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    type: LegacySourceType
    kind: SourceKind = "html"
    config: dict[str, Any] = Field(default_factory=dict)
    title: str | None = None
    url: str
    is_enabled: bool
    cadence: Literal["manual", "hourly", "daily", "weekly"] = "manual"
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    created_at: datetime


class SourceCreateIn(BaseModel):
    org_id: UUID
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=2048)
    kind: SourceKind = "html"
    config: dict[str, Any] = Field(default_factory=dict)
    title: str | None = Field(default=None, max_length=300)
    type: LegacySourceType | None = None

    @model_validator(mode="after")
    def _validate_payload(self) -> "SourceCreateIn":
        _validate_kind_config(self.kind, self.config)
        return self


class SourceUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    kind: SourceKind | None = None
    config: dict[str, Any] | None = None
    title: str | None = Field(default=None, max_length=300)
    type: LegacySourceType | None = None
    is_enabled: bool | None = None

    @model_validator(mode="after")
    def _validate_payload(self) -> "SourceUpdateIn":
        if (
            self.name is None
            and self.url is None
            and self.kind is None
            and self.config is None
            and self.title is None
            and self.type is None
            and self.is_enabled is None
        ):
            raise ValueError("At least one field must be provided")

        if self.kind is not None:
            _validate_kind_config(self.kind, self.config or {})
        return self


class SourceToggleIn(BaseModel):
    is_enabled: bool


class SourceScheduleIn(BaseModel):
    cadence: Literal["manual", "hourly", "daily", "weekly"]
