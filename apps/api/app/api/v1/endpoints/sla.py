from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.sla import OrgSlaRulesOut, OrgSlaRulesUpdateIn
from app.auth.roles import OrgRoleContext, enforce_org_role
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    ensure_org_sla_rules,
    get_org_sla_rules,
    rpc_record_audit_event,
    update_org_sla_rules,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


def _rules_payload(org_id: UUID, row: dict[str, object]) -> dict[str, object]:
    return {
        "org_id": row.get("org_id") or str(org_id),
        "enabled": bool(row.get("enabled", True)),
        "due_hours_low": int(row.get("due_hours_low") or 168),
        "due_hours_medium": int(row.get("due_hours_medium") or 72),
        "due_hours_high": int(row.get("due_hours_high") or 24),
        "due_soon_threshold_hours": int(row.get("due_soon_threshold_hours") or 12),
        "overdue_remind_every_hours": int(row.get("overdue_remind_every_hours") or 24),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _validate_due_order(
    *,
    due_hours_low: int,
    due_hours_medium: int,
    due_hours_high: int,
) -> None:
    if due_hours_low < due_hours_medium:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="due_hours_low must be greater than or equal to due_hours_medium",
        )
    if due_hours_medium < due_hours_high:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="due_hours_medium must be greater than or equal to due_hours_high",
        )


@router.get("/orgs/{org_id}/sla")
async def get_org_sla(
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> OrgSlaRulesOut:
    org_id_value = str(org_id)
    await enforce_org_role(auth, org_id_value, "admin")
    await ensure_org_sla_rules(auth.access_token, org_id_value)
    row = await get_org_sla_rules(auth.access_token, org_id_value)
    if not isinstance(row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load SLA rules.",
        )
    return OrgSlaRulesOut.model_validate(_rules_payload(org_id, row))


@router.put("/orgs/{org_id}/sla")
async def put_org_sla(
    org_id: UUID,
    payload: OrgSlaRulesUpdateIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> OrgSlaRulesOut:
    org_id_value = str(org_id)
    role_ctx: OrgRoleContext = await enforce_org_role(auth, org_id_value, "admin")
    await ensure_org_sla_rules(auth.access_token, org_id_value)

    current_row = await get_org_sla_rules(auth.access_token, org_id_value)
    if not isinstance(current_row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load SLA rules.",
        )

    patch = payload.model_dump(exclude_none=True)
    if patch:
        due_hours_low = int(patch.get("due_hours_low", current_row.get("due_hours_low") or 168))
        due_hours_medium = int(
            patch.get("due_hours_medium", current_row.get("due_hours_medium") or 72)
        )
        due_hours_high = int(patch.get("due_hours_high", current_row.get("due_hours_high") or 24))
        _validate_due_order(
            due_hours_low=due_hours_low,
            due_hours_medium=due_hours_medium,
            due_hours_high=due_hours_high,
        )

        row = await update_org_sla_rules(auth.access_token, org_id_value, patch)
    else:
        row = current_row

    if not isinstance(row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update SLA rules.",
        )

    if patch:
        await rpc_record_audit_event(
            auth.access_token,
            {
                "p_org_id": org_id_value,
                "p_action": "org_sla_rules_updated",
                "p_entity_type": "org_sla_rules",
                "p_entity_id": org_id_value,
                "p_metadata": {
                    "actor_user_id": role_ctx.user_id,
                    "changes": patch,
                },
            },
        )

    return OrgSlaRulesOut.model_validate(_rules_payload(org_id, row))
