from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ControlSeverity = Literal["low", "medium", "high"]
ControlEvidenceType = Literal["document", "screenshot", "log", "config", "ticket", "attestation"]
OrgControlStatus = Literal["not_started", "in_progress", "implemented", "needs_review"]
ControlConfidence = Literal["low", "medium", "high"]
FindingSeverity = Literal["low", "medium", "high", "critical"]


class ControlOut(BaseModel):
    id: UUID
    framework_slug: str
    control_key: str
    title: str
    description: str
    severity_default: ControlSeverity
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class ControlEvidenceItemOut(BaseModel):
    id: UUID
    control_id: UUID
    label: str
    description: str
    evidence_type: ControlEvidenceType
    required: bool
    sort_order: int
    created_at: datetime


class ControlGuidanceOut(BaseModel):
    id: UUID
    control_id: UUID
    guidance_markdown: str
    created_at: datetime


class ControlDetailOut(BaseModel):
    control: ControlOut
    evidence: list[ControlEvidenceItemOut] = Field(default_factory=list)
    guidance: ControlGuidanceOut | None = None


class InstallControlsFromTemplateIn(BaseModel):
    template_slug: str = Field(min_length=1, max_length=120)


class InstallControlsFromTemplateOut(BaseModel):
    installed: int


class OrgControlPatchIn(BaseModel):
    status: OrgControlStatus
    owner_user_id: UUID | None = None
    notes: str | None = None


class OrgControlLinkedFindingOut(BaseModel):
    finding_id: UUID
    title: str
    summary: str
    severity: FindingSeverity
    detected_at: datetime
    confidence: ControlConfidence


class OrgControlOut(BaseModel):
    id: UUID
    org_id: UUID
    control_id: UUID
    status: OrgControlStatus
    owner_user_id: UUID | None = None
    notes: str | None = None
    created_at: datetime
    framework_slug: str
    control_key: str
    title: str
    description: str
    severity_default: ControlSeverity
    tags: list[str] = Field(default_factory=list)
    evidence_count: int = 0
    linked_findings: list[OrgControlLinkedFindingOut] = Field(default_factory=list)


class FindingControlOut(BaseModel):
    id: UUID
    org_id: UUID
    finding_id: UUID
    control_id: UUID
    confidence: ControlConfidence
    created_at: datetime
    framework_slug: str
    control_key: str
    title: str
    severity_default: ControlSeverity
    tags: list[str] = Field(default_factory=list)


class LinkFindingToControlIn(BaseModel):
    org_id: UUID
    control_id: UUID
    confidence: ControlConfidence = "medium"


class LinkFindingToControlOut(BaseModel):
    ok: bool


class ControlSuggestionOut(BaseModel):
    control_id: UUID
    framework_slug: str
    control_key: str
    title: str
    confidence: ControlConfidence
    reasons: list[str] = Field(default_factory=list)

