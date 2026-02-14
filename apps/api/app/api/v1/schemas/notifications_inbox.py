from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

NotificationEventType = Literal["digest", "immediate_alert"]
NotificationEntityType = Literal["alert", "task", "export", "system"]
NotificationDeliveryStatus = Literal["queued", "sent", "failed"]


class NotificationEventOut(BaseModel):
    id: UUID
    org_id: UUID
    user_id: UUID | None = None
    job_id: UUID
    type: NotificationEventType
    entity_type: NotificationEntityType | None = None
    entity_id: UUID | None = None
    subject: str
    status: NotificationDeliveryStatus
    attempts: int
    last_error: str | None = None
    sent_at: datetime | None = None
    created_at: datetime
    read_at: datetime | None = None
    is_read: bool = False


class NotificationInboxOut(BaseModel):
    events: list[NotificationEventOut]


class NotificationReadStateOut(BaseModel):
    ok: bool = True


class NotificationRequeueOut(BaseModel):
    ok: bool = True
    job_id: UUID
