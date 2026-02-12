from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.monitoring import (
    AlertOut,
    AlertUpdateIn,
    AuditOut,
    FindingExplanationOut,
    FindingOut,
    MonitorRunCreateIn,
    MonitorRunOut,
    MonitorRunQueuedOut,
)
from app.core.settings import get_settings
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    rpc_append_audit,
    rpc_create_monitor_run,
    rpc_set_alert_status,
    select_alerts,
    select_audit_log,
    select_finding_explanations_by_org,
    select_findings,
    select_latest_finding_explanation,
    select_latest_snapshot_for_run,
    select_monitor_runs,
    select_task_evidence,
    select_tasks_for_alert,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/findings")
async def findings(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[FindingOut]]:
    rows = await select_findings(auth.access_token, str(org_id))
    explanation_rows = await select_finding_explanations_by_org(auth.access_token, str(org_id))
    finding_ids_with_explanations = {
        str(row.get("finding_id")) for row in explanation_rows if isinstance(row.get("finding_id"), str)
    }

    result: list[FindingOut] = []
    for row in rows:
        enriched = dict(row)
        run_id = row.get("run_id")
        if isinstance(run_id, str):
            snapshot = await select_latest_snapshot_for_run(auth.access_token, run_id)
            if snapshot:
                enriched["canonical_title"] = snapshot.get("canonical_title")
                enriched["item_published_at"] = snapshot.get("item_published_at")
        enriched["has_explanation"] = str(row.get("id")) in finding_ids_with_explanations
        result.append(FindingOut.model_validate(enriched))
    return {"findings": result}


@router.get("/findings/{finding_id}/explanation")
async def finding_explanation(
    finding_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> FindingExplanationOut:
    row = await select_latest_finding_explanation(auth.access_token, str(finding_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Explanation not found")
    return FindingExplanationOut.model_validate(row)


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
        evidence_count = 0
        linked_tasks = await select_tasks_for_alert(auth.access_token, str(alert_id))
        for task in linked_tasks:
            task_id = task.get("id")
            if not isinstance(task_id, str):
                continue
            evidence_count += len(await select_task_evidence(auth.access_token, task_id))

        if evidence_count < settings.ALERT_RESOLVE_MIN_EVIDENCE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Add evidence to a remediation task before resolving this alert.",
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
