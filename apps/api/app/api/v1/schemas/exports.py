from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ExportFormat = Literal["pdf", "csv"]
ExportStatus = Literal["queued", "running", "succeeded", "failed"]


class ExportCreateIn(BaseModel):
    org_id: UUID
    format: ExportFormat
    from_ts: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    include: list[str] | None = None


class ExportCreateOut(BaseModel):
    id: UUID
    status: Literal["queued"]


class ExportOut(BaseModel):
    id: UUID
    org_id: UUID
    requested_by_user_id: UUID | None = None
    format: ExportFormat
    scope: dict[str, Any]
    status: ExportStatus
    file_path: str | None = None
    file_sha256: str | None = None
    error_text: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ExportDownloadUrlOut(BaseModel):
    downloadUrl: str
    expiresIn: int
