from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.monitoring import (
    AlertOut,
    AlertUpdateIn,
    AuditOut,
    FindingOut,
    MonitorRunCreateIn,
    MonitorRunOut,
)
from app.core.integration_crypto import decrypt_integration_secret
from app.core.settings import get_settings
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    count_alert_task_evidence,
    rpc_append_audit,
    rpc_create_monitor_run,
    rpc_set_alert_status,
    rpc_upsert_alert_for_finding,
    rpc_upsert_finding,
    select_alerts,
    select_audit_log,
    select_findings,
    select_integration,
    select_monitor_runs,
)
from app.integrations.models import AlertNotification
from app.integrations.registry import create_connector

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


async def _notify_slack_for_alert_if_configured(
    access_token: str,
    org_id: str,
    alert: AlertNotification,
) -> None:
    row = await select_integration(access_token, org_id, "slack")
    if not row or row.get("status") != "enabled":
        return

    config = row.get("config")
    webhook_encrypted = config.get("webhook_encrypted") if isinstance(config, dict) else None
    if not isinstance(webhook_encrypted, str):
        return

    webhook_url = decrypt_integration_secret(webhook_encrypted)
    connector = create_connector("slack", webhook_url)
    await connector.send_alert(alert)


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
) -> dict[str, object]:
    settings = get_settings()
    run_id = await rpc_create_monitor_run(
        auth.access_token,
        {"p_org_id": str(payload.org_id), "p_source_id": str(payload.source_id)},
    )

    finding_ids: list[UUID] = []
    alert_ids: list[UUID] = []
    for finding in payload.findings:
        finding_id_str = await rpc_upsert_finding(
            auth.access_token,
            {
                "p_org_id": str(payload.org_id),
                "p_source_id": str(payload.source_id),
                "p_run_id": run_id,
                "p_title": finding.title,
                "p_summary": finding.summary,
                "p_severity": finding.severity,
                "p_fingerprint": finding.fingerprint,
                "p_raw_url": finding.raw_url,
                "p_raw_hash": finding.raw_hash,
            },
        )
        finding_id = UUID(finding_id_str)
        finding_ids.append(finding_id)

        alert_result = await rpc_upsert_alert_for_finding(
            auth.access_token,
            {"p_org_id": str(payload.org_id), "p_finding_id": finding_id_str},
        )
        alert_id = UUID(alert_result["id"])
        alert_ids.append(alert_id)

        if settings.SLACK_ALERT_NOTIFICATIONS_ENABLED and alert_result["created"]:
            try:
                await _notify_slack_for_alert_if_configured(
                    auth.access_token,
                    str(payload.org_id),
                    AlertNotification(
                        alert_id=str(alert_id),
                        org_id=str(payload.org_id),
                        finding_id=str(finding_id),
                        title=finding.title,
                        summary=finding.summary,
                        severity=finding.severity,
                    ),
                )
            except HTTPException as exc:
                await rpc_append_audit(
                    auth.access_token,
                    {
                        "p_org_id": str(payload.org_id),
                        "p_action": "slack_notify_failed",
                        "p_entity_type": "alert",
                        "p_entity_id": str(alert_id),
                        "p_metadata": {"detail": exc.detail},
                    },
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
                "findings_count": len(finding_ids),
            },
        },
    )

    return {"id": UUID(run_id), "findings": finding_ids, "alerts": alert_ids}
