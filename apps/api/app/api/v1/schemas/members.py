from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

OrgMemberRole = Literal["owner", "admin", "member", "viewer"]
OrgInviteRole = Literal["admin", "member", "viewer"]


class OrgMemberOut(BaseModel):
    org_id: UUID
    user_id: UUID
    role: OrgMemberRole
    created_at: datetime


class OrgMemberRoleUpdateIn(BaseModel):
    role: OrgMemberRole


class OrgInviteCreateIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: OrgInviteRole = "member"
    expires_hours: int = Field(default=72, ge=1, le=720)


class OrgInviteOut(BaseModel):
    id: UUID
    org_id: UUID
    email: str
    role: OrgInviteRole
    invited_by: UUID | None = None
    expires_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime


class OrgInviteCreateOut(BaseModel):
    invite_id: UUID
    email: str
    role: OrgInviteRole
    expires_at: datetime
    invite_link: str | None = None


class InviteAcceptIn(BaseModel):
    token: str = Field(min_length=1, max_length=2048)


class InviteAcceptOut(BaseModel):
    org_id: UUID
