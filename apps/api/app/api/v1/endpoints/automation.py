from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.automation import (
    AlertCreateTaskNowIn,
    AlertCreateTaskNowOut,
    AlertTaskRulesOut,
    AlertTaskRulesUpdateIn,
)
from app.auth.roles import enforce_org_role
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    bulk_insert_task_controls,
    ensure_alert_task_rules,
    get_alert_task_rules,
    list_control_evidence_items,
    rpc_add_task_evidence,
    rpc_compute_task_due_at,
    rpc_create_task,
    select_alert_by_id_for_org,
    select_finding_by_id,
    update_alert_task_id,
    update_alert_task_rules,
    update_task_service,
)
from app.services.alert_task import (
    build_task_description,
    build_task_title,
    checklist_evidence_items,
    resolve_control_ids_for_alert,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


def _rules_output_payload(org_id: UUID, row: dict[str, object]) -> dict[str, object]:
    return {
        "org_id": row.get("org_id") or str(org_id),
        "enabled": bool(row.get("enabled", True)),
        "auto_create_task_on_alert": bool(row.get("auto_create_task_on_alert", True)),
        "min_severity": row.get("min_severity") or "medium",
        "auto_link_suggested_controls": bool(row.get("auto_link_suggested_controls", True)),
        "auto_add_evidence_checklist": bool(row.get("auto_add_evidence_checklist", True)),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


async def _create_task_now(access_token: str, org_id: str, alert_id: str) -> str:
    alert_row = await select_alert_by_id_for_org(access_token, org_id, alert_id)
    if alert_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    existing_task_id = alert_row.get("task_id")
    if isinstance(existing_task_id, str) and existing_task_id.strip():
        return existing_task_id.strip()

    finding_id = alert_row.get("finding_id")
    if not isinstance(finding_id, str) or not finding_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Alert is missing finding_id.")

    finding_row = await select_finding_by_id(access_token, finding_id)
    if finding_row is None or finding_row.get("org_id") != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")

    raw_severity = str(finding_row.get("severity") or "medium").strip().lower()
    if raw_severity == "critical":
        severity = "high"
    elif raw_severity in {"low", "medium", "high"}:
        severity = raw_severity
    else:
        severity = "medium"
    due_at = await rpc_compute_task_due_at(
        access_token,
        org_id=org_id,
        severity=severity,
        created_at=(
            str(alert_row.get("created_at")).strip()
            if isinstance(alert_row.get("created_at"), str) and str(alert_row.get("created_at")).strip()
            else None
        ),
    )

    task_id = await rpc_create_task(
        access_token,
        {
            "p_org_id": org_id,
            "p_title": build_task_title(finding_row),
            "p_description": build_task_description(finding_row),
            "p_alert_id": alert_id,
            "p_finding_id": finding_id,
            "p_due_at": due_at,
        },
    )
    await update_task_service(
        task_id,
        {"severity": severity, "sla_state": "on_track"},
    )
    await update_alert_task_id(access_token, org_id, alert_id, task_id)

    await ensure_alert_task_rules(access_token, org_id)
    await get_alert_task_rules(access_token, org_id)

    control_ids = await resolve_control_ids_for_alert(
        access_token,
        org_id=org_id,
        finding_id=finding_id,
        finding_row=finding_row,
        allow_suggestions=True,
    )
    if control_ids:
        await bulk_insert_task_controls(access_token, org_id, task_id, control_ids)

    evidence_rows = await list_control_evidence_items(access_token, control_ids) if control_ids else []
    evidence_items = checklist_evidence_items(evidence_rows)
    for item in evidence_items:
        await rpc_add_task_evidence(
            access_token,
            {
                "p_task_id": task_id,
                "p_type": item["type"],
                "p_ref": item["ref"],
            },
        )

    return task_id


@router.get("/orgs/{org_id}/automation/alert-task-rules")
async def get_org_alert_task_rules(
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> AlertTaskRulesOut:
    org_id_value = str(org_id)
    await enforce_org_role(auth, org_id_value, "admin")
    await ensure_alert_task_rules(auth.access_token, org_id_value)
    row = await get_alert_task_rules(auth.access_token, org_id_value)
    if not isinstance(row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to load automation rules.",
        )
    return AlertTaskRulesOut.model_validate(_rules_output_payload(org_id, row))


@router.put("/orgs/{org_id}/automation/alert-task-rules")
async def put_org_alert_task_rules(
    org_id: UUID,
    payload: AlertTaskRulesUpdateIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> AlertTaskRulesOut:
    org_id_value = str(org_id)
    await enforce_org_role(auth, org_id_value, "admin")
    await ensure_alert_task_rules(auth.access_token, org_id_value)

    patch = payload.model_dump(exclude_none=True)
    if patch:
        row = await update_alert_task_rules(auth.access_token, org_id_value, patch)
    else:
        row = await get_alert_task_rules(auth.access_token, org_id_value)

    if not isinstance(row, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update automation rules.",
        )
    return AlertTaskRulesOut.model_validate(_rules_output_payload(org_id, row))


@router.post("/alerts/{alert_id}/create-task-now")
async def create_task_now(
    alert_id: UUID,
    payload: AlertCreateTaskNowIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> AlertCreateTaskNowOut:
    task_id = await _create_task_now(auth.access_token, str(payload.org_id), str(alert_id))
    return AlertCreateTaskNowOut(task_id=UUID(task_id))
