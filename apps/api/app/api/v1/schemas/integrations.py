from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

IntegrationType = Literal["slack", "jira"]
IntegrationStatus = Literal["connected", "disabled"]


class IntegrationOut(BaseModel):
    id: UUID
    org_id: UUID
    type: IntegrationType
    status: IntegrationStatus
    config: dict[str, Any]
    updated_at: datetime


class SlackConnectIn(BaseModel):
    org_id: UUID
    webhook_url: str = Field(min_length=1, max_length=4096)


class JiraConnectIn(BaseModel):
    org_id: UUID
    base_url: str = Field(min_length=1, max_length=2048)
    email: str = Field(min_length=3, max_length=320)
    api_token: str = Field(min_length=1, max_length=2048)
    project_key: str = Field(min_length=1, max_length=64)


class OrgIntegrationIn(BaseModel):
    org_id: UUID


class SlackNotifyIn(BaseModel):
    org_id: UUID
    alert_id: UUID


class JiraCreateIssueOut(BaseModel):
    issueKey: str
    url: str
