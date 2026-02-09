from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

IntegrationType = Literal["slack", "jira", "github"]
IntegrationStatus = Literal["enabled", "disabled"]


class IntegrationOut(BaseModel):
    id: UUID
    org_id: UUID
    type: IntegrationType
    status: IntegrationStatus
    has_secret: bool
    created_at: datetime
    updated_at: datetime


class SlackConnectIn(BaseModel):
    org_id: UUID
    webhook_url: str = Field(min_length=1, max_length=4096)
    status: IntegrationStatus = "enabled"


class SlackTestIn(BaseModel):
    org_id: UUID
    message: str | None = Field(default=None, max_length=2000)
