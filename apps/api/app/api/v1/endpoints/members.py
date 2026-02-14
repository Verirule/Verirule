from __future__ import annotations

import logging
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool

from app.api.v1.schemas.members import (
    InviteAcceptIn,
    InviteAcceptOut,
    OrgInviteCreateIn,
    OrgInviteCreateOut,
    OrgInviteOut,
    OrgMemberOut,
    OrgMemberRoleUpdateIn,
)
from app.auth.roles import OrgRoleContext, enforce_org_role
from app.billing.entitlements import get_entitlements
from app.core.settings import get_settings
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    count_org_members_by_role_service,
    delete_org_invite,
    delete_org_member_service,
    rpc_accept_org_invite,
    rpc_create_org_invite,
    rpc_record_audit_event,
    select_org_billing,
    select_org_invite_by_id,
    select_org_invites,
    select_org_member_service,
    select_org_members_service,
    update_org_member_role_service,
)
from app.services.email import (
    InviteEmailNotConfiguredError,
    InviteEmailSendError,
    send_org_invite_email,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)
logger = logging.getLogger(__name__)


def _is_production() -> bool:
    env = get_settings().VERIRULE_ENV.strip().lower()
    return env in {"production", "prod"}


def _invite_link(token: str) -> str:
    site_url = get_settings().NEXT_PUBLIC_SITE_URL.strip() or "https://www.verirule.com"
    return f"{site_url.rstrip('/')}/invite/accept?token={quote(token, safe='')}"


def _as_uuid_or_none(value: str | None) -> UUID | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return UUID(value.strip())
    except ValueError:
        return None


def _clean_role(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid {field_name} response from Supabase.",
        )
    return value.strip().lower()


@router.get("/orgs/{org_id}/members")
async def list_org_members(
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[OrgMemberOut]]:
    await enforce_org_role(auth, str(org_id), "member")
    rows = await select_org_members_service(str(org_id))
    return {"members": [OrgMemberOut.model_validate(row) for row in rows]}


@router.patch("/orgs/{org_id}/members/{user_id}")
async def update_org_member_role(
    org_id: UUID,
    user_id: UUID,
    payload: OrgMemberRoleUpdateIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> OrgMemberOut:
    role_ctx: OrgRoleContext = await enforce_org_role(auth, str(org_id), "admin")

    existing = await select_org_member_service(str(org_id), str(user_id))
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization member not found.")

    current_role = _clean_role(existing.get("role"), field_name="organization member")
    if current_role == "owner" and role_ctx.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if payload.role == "owner" and role_ctx.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if current_role == "owner" and payload.role != "owner":
        owner_count = await count_org_members_by_role_service(str(org_id), "owner")
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot change the role of the last owner.",
            )

    updated = await update_org_member_role_service(str(org_id), str(user_id), payload.role)

    if payload.role != current_role:
        await rpc_record_audit_event(
            auth.access_token,
            {
                "p_org_id": str(org_id),
                "p_action": "org_member_role_changed",
                "p_entity_type": "org_member",
                "p_entity_id": str(user_id),
                "p_metadata": {
                    "previous_role": current_role,
                    "new_role": payload.role,
                    "actor_user_id": role_ctx.user_id,
                    "target_user_id": str(user_id),
                },
            },
        )

    return OrgMemberOut.model_validate(updated)


@router.delete("/orgs/{org_id}/members/{user_id}")
async def remove_org_member(
    org_id: UUID,
    user_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, bool]:
    role_ctx: OrgRoleContext = await enforce_org_role(auth, str(org_id), "admin")

    existing = await select_org_member_service(str(org_id), str(user_id))
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization member not found.")

    target_role = _clean_role(existing.get("role"), field_name="organization member")
    if target_role == "owner" and role_ctx.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if target_role == "owner":
        owner_count = await count_org_members_by_role_service(str(org_id), "owner")
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last owner.",
            )

    await delete_org_member_service(str(org_id), str(user_id))

    await rpc_record_audit_event(
        auth.access_token,
        {
            "p_org_id": str(org_id),
            "p_action": "org_member_removed",
            "p_entity_type": "org_member",
            "p_entity_id": str(user_id),
            "p_metadata": {
                "removed_role": target_role,
                "actor_user_id": role_ctx.user_id,
                "target_user_id": str(user_id),
            },
        },
    )

    return {"ok": True}


@router.post("/orgs/{org_id}/invites")
async def create_org_invite(
    org_id: UUID,
    payload: OrgInviteCreateIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> OrgInviteCreateOut:
    role_ctx: OrgRoleContext = await enforce_org_role(auth, str(org_id), "admin")
    billing_row = await select_org_billing(auth.access_token, str(org_id))
    raw_plan = billing_row.get("plan") if isinstance(billing_row, dict) else None
    entitlements = get_entitlements(raw_plan if isinstance(raw_plan, str) else None)

    if entitlements.max_members is not None:
        member_rows = await select_org_members_service(str(org_id))
        pending_invites = await select_org_invites(auth.access_token, str(org_id), pending_only=True)
        seats_in_use = len(member_rows) + len(pending_invites)
        if seats_in_use >= entitlements.max_members:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Member limit reached ({entitlements.max_members}). Upgrade required.",
            )

    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="email is required")

    rpc_row = await rpc_create_org_invite(
        auth.access_token,
        {
            "p_org_id": str(org_id),
            "p_email": email,
            "p_role": payload.role,
            "p_expires_hours": payload.expires_hours,
        },
    )

    invite_id = rpc_row.get("invite_id")
    token = rpc_row.get("token")
    if not isinstance(invite_id, str) or not isinstance(token, str) or not token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create invite response from Supabase.",
        )

    invite_row = await select_org_invite_by_id(auth.access_token, str(org_id), invite_id)
    if not isinstance(invite_row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch newly created invite.",
        )

    link = _invite_link(token)
    expose_link: str | None = None
    try:
        await run_in_threadpool(
            send_org_invite_email,
            recipient_email=email,
            invite_link=link,
            org_id=str(org_id),
            role=payload.role,
        )
    except InviteEmailNotConfiguredError:
        if _is_production():
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Invite email delivery is not configured.",
            ) from None
        expose_link = link
        logger.info(
            "Invite email transport not configured; returning invite link in API response.",
            extra={
                "org_id": str(org_id),
                "actor_user_id": role_ctx.user_id,
                "email_domain": email.split("@")[-1] if "@" in email else None,
            },
        )
    except InviteEmailSendError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send invite email.",
        ) from exc

    await rpc_record_audit_event(
        auth.access_token,
        {
            "p_org_id": str(org_id),
            "p_action": "org_invite_created",
            "p_entity_type": "org_invite",
            "p_entity_id": invite_id,
            "p_metadata": {
                "email": email,
                "role": payload.role,
                "expires_at": invite_row.get("expires_at"),
                "invited_by": role_ctx.user_id,
            },
        },
    )

    return OrgInviteCreateOut.model_validate(
        {
            "invite_id": invite_id,
            "email": invite_row.get("email"),
            "role": invite_row.get("role"),
            "expires_at": invite_row.get("expires_at"),
            "invite_link": expose_link,
        }
    )


@router.get("/orgs/{org_id}/invites")
async def list_org_invites(
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[OrgInviteOut]]:
    await enforce_org_role(auth, str(org_id), "admin")
    rows = await select_org_invites(auth.access_token, str(org_id), pending_only=True)
    return {"invites": [OrgInviteOut.model_validate(row) for row in rows]}


@router.delete("/orgs/{org_id}/invites/{invite_id}")
async def revoke_org_invite(
    org_id: UUID,
    invite_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, bool]:
    role_ctx: OrgRoleContext = await enforce_org_role(auth, str(org_id), "admin")
    await delete_org_invite(auth.access_token, str(org_id), str(invite_id))

    await rpc_record_audit_event(
        auth.access_token,
        {
            "p_org_id": str(org_id),
            "p_action": "org_invite_revoked",
            "p_entity_type": "org_invite",
            "p_entity_id": str(invite_id),
            "p_metadata": {
                "actor_user_id": role_ctx.user_id,
            },
        },
    )

    return {"ok": True}


@router.post("/invites/accept")
async def accept_org_invite(
    payload: InviteAcceptIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> InviteAcceptOut:
    token = payload.token.strip()
    org_id = await rpc_accept_org_invite(auth.access_token, {"p_token": token})

    actor_user_id = _as_uuid_or_none(auth.claims.get("sub") if isinstance(auth.claims.get("sub"), str) else None)
    await rpc_record_audit_event(
        auth.access_token,
        {
            "p_org_id": org_id,
            "p_action": "org_invite_accepted",
            "p_entity_type": "org_membership",
            "p_entity_id": str(actor_user_id) if actor_user_id else None,
            "p_metadata": {
                "accepted_by": auth.claims.get("sub"),
            },
        },
    )

    return InviteAcceptOut(org_id=UUID(org_id))
