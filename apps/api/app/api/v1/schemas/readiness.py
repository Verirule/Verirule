from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OrgReadinessSnapshotOut(BaseModel):
    id: UUID
    org_id: UUID
    computed_at: datetime
    score: int = Field(ge=0, le=100)
    controls_total: int
    controls_with_evidence: int
    evidence_items_total: int
    evidence_items_done: int
    open_alerts_high: int
    open_tasks: int
    overdue_tasks: int
    metadata: dict[str, Any]


class OrgReadinessComputeOut(BaseModel):
    snapshot_id: UUID
    readiness: OrgReadinessSnapshotOut
