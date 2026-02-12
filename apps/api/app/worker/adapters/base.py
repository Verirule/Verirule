from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator

SourceKind = Literal["html", "rss", "pdf", "github_releases"]


class Source(BaseModel):
    id: str
    org_id: str
    url: str
    kind: SourceKind = "html"
    config: dict[str, Any] = Field(default_factory=dict)
    name: str | None = None
    type: str | None = None
    title: str | None = None
    is_enabled: bool = True
    etag: str | None = None
    last_modified: str | None = None
    content_type: str | None = None
    fetch_timeout_seconds: float = 10.0
    fetch_max_bytes: int = 1_000_000

    @field_validator("config", mode="before")
    @classmethod
    def _normalize_config(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}


class Snapshot(BaseModel):
    id: str | None = None
    org_id: str | None = None
    source_id: str | None = None
    run_id: str | None = None
    content_hash: str | None = None
    text_fingerprint: str | None = None
    text_preview: str | None = None
    canonical_text: str | None = None
    item_id: str | None = None
    item_published_at: datetime | None = None
    etag: str | None = None
    last_modified: str | None = None


class AdapterResult(BaseModel):
    canonical_title: str | None = None
    canonical_text: str = ""
    item_id: str | None = None
    item_published_at: datetime | None = None
    content_type: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    http_status: int = 200
    fetched_url: str | None = None
    content_len: int = 0
    raw_bytes_hash: str | None = None


class Adapter(Protocol):
    async def fetch(self, source: Source, prev_snapshot: Snapshot | None) -> AdapterResult:
        ...
