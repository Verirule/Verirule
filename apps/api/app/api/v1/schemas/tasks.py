from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


TaskStatus = Literal["open", "in_progress", "resolved", "blocked"]


class TaskOut(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    status: TaskStatus
    assignee_user_id: UUID | None = None
    alert_id: UUID | None = None
    finding_id: UUID | None = None
    due_at: datetime | None = None
    created_by_user_id: UUID
    created_at: datetime


class TaskCreateIn(BaseModel):
    org_id: UUID
    title: str = Field(min_length=1, max_length=300)
    alert_id: UUID | None = None
    finding_id: UUID | None = None
    due_at: datetime | None = None


class TaskPatchIn(BaseModel):
    assignee_user_id: UUID | None = None
    status: TaskStatus | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "TaskPatchIn":
        if self.assignee_user_id is None and self.status is None:
            raise ValueError("assignee_user_id or status must be provided")
        return self


class TaskCommentOut(BaseModel):
    id: UUID
    task_id: UUID
    author_user_id: UUID
    body: str
    created_at: datetime


class TaskCommentCreateIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class TaskEvidenceOut(BaseModel):
    id: UUID
    task_id: UUID
    type: Literal["link", "file", "log"]
    ref: str
    created_by_user_id: UUID
    created_at: datetime


class TaskEvidenceCreateIn(BaseModel):
    type: Literal["link", "file", "log"]
    ref: str = Field(min_length=1, max_length=4096)
