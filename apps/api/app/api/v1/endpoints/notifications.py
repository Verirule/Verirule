from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.notifications import (
    OrgNotificationRulesOut,
    OrgNotificationRulesUpdateIn,
    UserNotificationPrefsOut,
    UserNotificationPrefsUpdateIn,
)
from app.auth.roles import OrgRoleContext, enforce_org_role
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    ensure_org_notification_rules,
    ensure_user_notification_prefs,
    get_org_notification_rules,
    get_user_notification_prefs,
    rpc_record_audit_event,
    update_org_notification_rules,
    update_user_notification_prefs,
    upsert_my_email,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


def _claims_user_id(auth: VerifiedSupabaseAuth) -> str | None:
    sub = auth.claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        return None
    return sub.strip()


def _org_rules_payload(org_id: UUID, row: dict[str, object]) -> dict[str, object]:
    return {
        "org_id": row.get("org_id") or str(org_id),
        "enabled": bool(row.get("enabled", True)),
        "mode": row.get("mode") or "digest",
        "digest_cadence": row.get("digest_cadence") or "daily",
        "min_severity": row.get("min_severity") or "medium",
        "last_digest_sent_at": row.get("last_digest_sent_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _user_prefs_payload(auth: VerifiedSupabaseAuth, row: dict[str, object]) -> dict[str, object]:
    return {
        "user_id": row.get("user_id") or _claims_user_id(auth),
        "email_enabled": bool(row.get("email_enabled", True)),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


@router.get("/orgs/{org_id}/notifications/rules")
async def get_org_notifications_rules(
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> OrgNotificationRulesOut:
    org_id_value = str(org_id)
    await enforce_org_role(auth, org_id_value, "admin")
    await upsert_my_email(auth.access_token, org_id_value)
    await ensure_org_notification_rules(auth.access_token, org_id_value)
    row = await get_org_notification_rules(auth.access_token, org_id_value)
    if not isinstance(row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load notification rules.",
        )
    return OrgNotificationRulesOut.model_validate(_org_rules_payload(org_id, row))


@router.put("/orgs/{org_id}/notifications/rules")
async def put_org_notifications_rules(
    org_id: UUID,
    payload: OrgNotificationRulesUpdateIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> OrgNotificationRulesOut:
    org_id_value = str(org_id)
    role_ctx: OrgRoleContext = await enforce_org_role(auth, org_id_value, "admin")
    await upsert_my_email(auth.access_token, org_id_value)
    await ensure_org_notification_rules(auth.access_token, org_id_value)

    patch = payload.model_dump(exclude_none=True)
    if patch:
        row = await update_org_notification_rules(auth.access_token, org_id_value, patch)
    else:
        row = await get_org_notification_rules(auth.access_token, org_id_value)

    if not isinstance(row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update notification rules.",
        )

    if patch:
        await rpc_record_audit_event(
            auth.access_token,
            {
                "p_org_id": org_id_value,
                "p_action": "org_notification_rules_updated",
                "p_entity_type": "org_notification_rules",
                "p_entity_id": org_id_value,
                "p_metadata": {
                    "actor_user_id": role_ctx.user_id,
                    "changes": patch,
                },
            },
        )

    return OrgNotificationRulesOut.model_validate(_org_rules_payload(org_id, row))


@router.get("/me/notifications")
async def get_my_notification_prefs(
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> UserNotificationPrefsOut:
    await ensure_user_notification_prefs(auth.access_token)
    row = await get_user_notification_prefs(auth.access_token)
    if not isinstance(row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load notification preferences.",
        )
    return UserNotificationPrefsOut.model_validate(_user_prefs_payload(auth, row))


@router.put("/me/notifications")
async def put_my_notification_prefs(
    payload: UserNotificationPrefsUpdateIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> UserNotificationPrefsOut:
    await ensure_user_notification_prefs(auth.access_token)
    row = await update_user_notification_prefs(auth.access_token, payload.model_dump())
    if not isinstance(row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update notification preferences.",
        )
    return UserNotificationPrefsOut.model_validate(_user_prefs_payload(auth, row))
