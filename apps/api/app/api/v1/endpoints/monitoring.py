from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.monitoring import (
    AlertOut,
    AlertUpdateIn,
    AuditOut,
    FindingOut,
    MonitorRunCreateIn,
    MonitorRunOut,
    MonitorRunQueuedOut,
)
from app.core.settings import get_settings
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    count_alert_task_evidence,
    rpc_append_audit,
    rpc_create_monitor_run,
    rpc_set_alert_status,
    select_alerts,
    select_audit_log,
    select_findings,
    select_monitor_runs,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/findings")
async def findings(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[FindingOut]]:
    rows = await select_findings(auth.access_token, str(org_id))
    return {"findings": [FindingOut.model_validate(row) for row in rows]}


@router.get("/alerts")
async def alerts(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[AlertOut]]:
    rows = await select_alerts(auth.access_token, str(org_id))
    return {"alerts": [AlertOut.model_validate(row) for row in rows]}


@router.patch("/alerts/{alert_id}")
async def update_alert(
    alert_id: UUID, payload: AlertUpdateIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    settings = get_settings()
    if payload.status == "resolved" and settings.REQUIRE_ALERT_EVIDENCE_FOR_RESOLVE:
        evidence_count = await count_alert_task_evidence(auth.access_token, str(alert_id))
        if evidence_count < settings.ALERT_RESOLVE_MIN_EVIDENCE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Resolving alerts requires at least {settings.ALERT_RESOLVE_MIN_EVIDENCE} "
                    "evidence item(s) across linked tasks."
                ),
            )

    await rpc_set_alert_status(
        auth.access_token,
        {"p_alert_id": str(alert_id), "p_status": payload.status},
    )
    return {"ok": True}


@router.get("/audit")
async def audit_log(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[AuditOut]]:
    rows = await select_audit_log(auth.access_token, str(org_id))
    return {"audit": [AuditOut.model_validate(row) for row in rows]}


@router.get("/monitor/runs")
async def monitor_runs(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[MonitorRunOut]]:
    rows = await select_monitor_runs(auth.access_token, str(org_id))
    return {"runs": [MonitorRunOut.model_validate(row) for row in rows]}


@router.post("/monitor/run")
async def monitor_run(
    payload: MonitorRunCreateIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> MonitorRunQueuedOut:
    run_id = await rpc_create_monitor_run(
        auth.access_token,
        {"p_org_id": str(payload.org_id), "p_source_id": str(payload.source_id)},
    )

    await rpc_append_audit(
        auth.access_token,
        {
            "p_org_id": str(payload.org_id),
            "p_action": "monitor_run_queued",
            "p_entity_type": "monitor_run",
            "p_entity_id": run_id,
            "p_metadata": {
                "source_id": str(payload.source_id),
            },
        },
    )

    return MonitorRunQueuedOut(id=UUID(run_id), status="queued")
