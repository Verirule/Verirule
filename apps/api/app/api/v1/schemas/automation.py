from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

SeverityLevel = Literal["low", "medium", "high"]


class AlertTaskRulesOut(BaseModel):
    org_id: UUID
    enabled: bool
    auto_create_task_on_alert: bool
    min_severity: SeverityLevel
    auto_link_suggested_controls: bool
    auto_add_evidence_checklist: bool
    created_at: datetime
    updated_at: datetime


class AlertTaskRulesUpdateIn(BaseModel):
    enabled: bool | None = None
    auto_create_task_on_alert: bool | None = None
    min_severity: SeverityLevel | None = None
    auto_link_suggested_controls: bool | None = None
    auto_add_evidence_checklist: bool | None = None


class AlertCreateTaskNowIn(BaseModel):
    org_id: UUID


class AlertCreateTaskNowOut(BaseModel):
    task_id: UUID
