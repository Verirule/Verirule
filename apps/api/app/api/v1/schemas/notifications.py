from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

NotificationMode = Literal["digest", "immediate", "both"]
DigestCadence = Literal["daily", "weekly"]
SeverityLevel = Literal["low", "medium", "high"]


class OrgNotificationRulesOut(BaseModel):
    org_id: UUID
    enabled: bool
    mode: NotificationMode
    digest_cadence: DigestCadence
    min_severity: SeverityLevel
    last_digest_sent_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class OrgNotificationRulesUpdateIn(BaseModel):
    enabled: bool | None = None
    mode: NotificationMode | None = None
    digest_cadence: DigestCadence | None = None
    min_severity: SeverityLevel | None = None


class UserNotificationPrefsOut(BaseModel):
    user_id: UUID
    email_enabled: bool
    created_at: datetime
    updated_at: datetime


class UserNotificationPrefsUpdateIn(BaseModel):
    email_enabled: bool

