from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

TaskStatus = Literal["open", "in_progress", "blocked", "done"]
TaskEvidenceType = Literal["link", "file", "log"]


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
