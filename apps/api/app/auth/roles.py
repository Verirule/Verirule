from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import select_org_member_role

OrgRole = Literal["owner", "admin", "member", "viewer"]

role_rank: dict[str, int] = {
    "viewer": 1,
    "member": 2,
    "admin": 3,
    "owner": 4,
}

supabase_auth_dependency = Depends(verify_supabase_auth)


@dataclass(frozen=True)
class OrgRoleContext:
    org_id: str
    user_id: str
    role: OrgRole


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _claims_user_id(auth: VerifiedSupabaseAuth) -> str:
    sub = auth.claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise _unauthorized()
    return sub.strip()


def _normalize_role(value: str) -> OrgRole:
    normalized = value.strip().lower()
    if normalized not in role_rank:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid organization role configuration.",
        )
    return normalized  # type: ignore[return-value]


async def enforce_org_role(
    auth: VerifiedSupabaseAuth,
    org_id: str,
    min_role: OrgRole,
) -> OrgRoleContext:
    normalized_min = _normalize_role(min_role)
    user_id = _claims_user_id(auth)

    member_role = await select_org_member_role(auth.access_token, org_id, user_id)
    if not isinstance(member_role, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    normalized_member = _normalize_role(member_role)
    if role_rank[normalized_member] < role_rank[normalized_min]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return OrgRoleContext(org_id=org_id, user_id=user_id, role=normalized_member)


def require_org_role(min_role: OrgRole):
    async def dependency(
        org_id: UUID,
        auth: VerifiedSupabaseAuth = supabase_auth_dependency,
    ) -> OrgRoleContext:
        return await enforce_org_role(auth, str(org_id), min_role)

    return Depends(dependency)
