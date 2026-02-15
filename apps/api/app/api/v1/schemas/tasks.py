from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TaskStatus = Literal["open", "in_progress", "blocked", "done"]
TaskEvidenceType = Literal["link", "file", "log"]
TaskSlaState = Literal["none", "on_track", "due_soon", "overdue"]


class TaskOut(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    description: str | None = None
    status: TaskStatus
    assignee_user_id: UUID | None = None
    alert_id: UUID | None = None
    finding_id: UUID | None = None
    due_at: datetime | None = None
    severity: str | None = None
    sla_state: TaskSlaState = "none"
    created_at: datetime
    updated_at: datetime


class TaskCreateIn(BaseModel):
    org_id: UUID
    title: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    alert_id: UUID | None = None
    finding_id: UUID | None = None
    due_at: datetime | None = None


class TaskStatusIn(BaseModel):
    status: TaskStatus


class TaskCommentOut(BaseModel):
    id: UUID
    task_id: UUID
    author_user_id: UUID | None = None
    body: str
    created_at: datetime


class TaskCommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class TaskEvidenceOut(BaseModel):
    id: UUID
    task_id: UUID
    type: TaskEvidenceType
    ref: str
    created_at: datetime


class TaskEvidenceIn(BaseModel):
    type: TaskEvidenceType
    ref: str = Field(min_length=1, max_length=4096)


class TaskEvidenceUploadUrlIn(BaseModel):
    filename: str = Field(min_length=1, max_length=180)
    content_type: str | None = Field(default=None, min_length=1, max_length=120)


class TaskEvidenceUploadUrlOut(BaseModel):
    path: str
    uploadUrl: str
    expiresIn: int


class TaskEvidenceFileIn(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


class TaskEvidenceDownloadUrlOut(BaseModel):
    downloadUrl: str
    expiresIn: int


class EvidenceFileUploadUrlIn(BaseModel):
    org_id: UUID
    filename: str = Field(min_length=1, max_length=180)
    content_type: str | None = Field(default=None, min_length=1, max_length=120)
    byte_size: int = Field(gt=0)


class EvidenceFileUploadUrlOut(BaseModel):
    evidence_file_id: UUID
    bucket: str
    path: str
    signed_upload_url: str
    expires_in: int


class EvidenceFileFinalizeIn(BaseModel):
    org_id: UUID
    sha256: str = Field(min_length=64, max_length=64, pattern=r"^[a-fA-F0-9]{64}$")


class EvidenceFileOut(BaseModel):
    id: UUID
    org_id: UUID
    task_id: UUID
    filename: str
    storage_bucket: str
    storage_path: str
    content_type: str | None = None
    byte_size: int | None = None
    sha256: str | None = None
    uploaded_by: UUID | None = None
    created_at: datetime


class EvidenceFileDownloadUrlOut(BaseModel):
    download_url: str
    expires_in: int
