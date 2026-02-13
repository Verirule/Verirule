from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class MonitorRunOut(BaseModel):
    id: UUID
    org_id: UUID
    source_id: UUID
    status: Literal["queued", "running", "succeeded", "failed"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    created_at: datetime


class FindingOut(BaseModel):
    id: UUID
    org_id: UUID
    source_id: UUID
    run_id: UUID
    title: str
    summary: str
    severity: Literal["low", "medium", "high", "critical"]
    detected_at: datetime
    fingerprint: str
    raw_url: str | None = None
    raw_hash: str | None = None
    canonical_title: str | None = None
    item_published_at: datetime | None = None
    has_explanation: bool = False


class FindingExplanationOut(BaseModel):
    id: UUID
    org_id: UUID
    finding_id: UUID
    summary: str
    diff_preview: str | None = None
    citations: list[dict[str, str]]
    created_at: datetime


class AlertOut(BaseModel):
    id: UUID
    org_id: UUID
    finding_id: UUID
    task_id: UUID | None = None
    status: Literal["open", "acknowledged", "resolved"]
    owner_user_id: UUID | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class AlertUpdateIn(BaseModel):
    status: Literal["acknowledged", "resolved"]


class AuditOut(BaseModel):
    id: UUID
    org_id: UUID
    actor_user_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: UUID | None = None
    metadata: dict[str, Any]
    created_at: datetime


class MonitorRunCreateIn(BaseModel):
    org_id: UUID
    source_id: UUID


class MonitorRunQueuedOut(BaseModel):
    id: UUID
    status: Literal["queued"]
