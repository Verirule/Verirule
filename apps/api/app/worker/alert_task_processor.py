from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.core.supabase_rest import (
    bulk_insert_task_controls_service,
    bulk_insert_task_evidence_service,
    ensure_alert_task_rules,
    get_alert_task_rules,
    insert_task_service,
    list_control_evidence_items,
    rpc_compute_task_due_at,
    select_alerts_needing_tasks_service,
    select_finding_by_id,
    update_alert_task_id,
)
from app.services.alert_task import (
    build_task_description,
    build_task_title,
    checklist_evidence_items,
    normalize_alert_task_rules,
    resolve_control_ids_for_alert,
    severity_meets_minimum,
)
from app.worker.retry import sanitize_error

ALERT_TASK_BATCH_LIMIT = 25
logger = get_logger("worker.alert_tasks")


class AlertTaskProcessor:
    def __init__(self, *, access_token: str) -> None:
        self.access_token = access_token

    async def process_alerts_once(self, *, limit: int = ALERT_TASK_BATCH_LIMIT) -> int:
        alert_rows = await select_alerts_needing_tasks_service(limit=limit)
        created_count = 0
        for alert_row in alert_rows:
            try:
                created = await self._process_single_alert(alert_row)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.error(
                    "alert_task.processor_error",
                    extra={
                        "component": "worker",
                        "error": sanitize_error(exc, default_message="alert task automation failed"),
                    },
                )
                continue
            if created:
                created_count += 1
        return created_count

    async def _process_single_alert(self, alert_row: dict[str, Any]) -> bool:
        alert_id = str(alert_row.get("id") or "").strip()
        org_id = str(alert_row.get("org_id") or "").strip()
        finding_id = str(alert_row.get("finding_id") or "").strip()
        status = str(alert_row.get("status") or "").strip().lower()
        existing_task_id = str(alert_row.get("task_id") or "").strip()

        if not alert_id or not org_id or not finding_id:
            return False
        if existing_task_id or status != "open":
            return False

        await ensure_alert_task_rules(self.access_token, org_id)
        rules_row = await get_alert_task_rules(self.access_token, org_id)
        rules = normalize_alert_task_rules(rules_row if isinstance(rules_row, dict) else None)
        if not rules["enabled"] or not rules["auto_create_task_on_alert"]:
            return False

        finding_row = await select_finding_by_id(self.access_token, finding_id)
        if finding_row is None or str(finding_row.get("org_id") or "") != org_id:
            return False
        if not severity_meets_minimum(
            str(finding_row.get("severity") or "medium"), str(rules.get("min_severity") or "medium")
        ):
            return False

        raw_severity = str(finding_row.get("severity") or "medium").strip().lower()
        if raw_severity == "critical":
            severity = "high"
        elif raw_severity in {"low", "medium", "high"}:
            severity = raw_severity
        else:
            severity = "medium"
        due_at = await rpc_compute_task_due_at(
            self.access_token,
            org_id=org_id,
            severity=severity,
            created_at=(
                str(alert_row.get("created_at")).strip()
                if isinstance(alert_row.get("created_at"), str) and str(alert_row.get("created_at")).strip()
                else None
            ),
        )

        task_id = await insert_task_service(
            org_id,
            title=build_task_title(finding_row),
            description=build_task_description(finding_row),
            alert_id=alert_id,
            finding_id=finding_id,
            due_at=due_at,
            severity=severity,
            sla_state="on_track",
        )
        await update_alert_task_id(self.access_token, org_id, alert_id, task_id)

        control_ids = await resolve_control_ids_for_alert(
            self.access_token,
            org_id=org_id,
            finding_id=finding_id,
            finding_row=finding_row,
            allow_suggestions=bool(rules.get("auto_link_suggested_controls")),
        )
        if control_ids:
            await bulk_insert_task_controls_service(org_id, task_id, control_ids)

        if control_ids and bool(rules.get("auto_add_evidence_checklist")):
            evidence_rows = await list_control_evidence_items(self.access_token, control_ids)
            checklist_items = checklist_evidence_items(evidence_rows)
            if checklist_items:
                await bulk_insert_task_evidence_service(org_id, task_id, checklist_items)

        logger.info(
            "alert_task.created",
            extra={
                "component": "worker",
                "alert_id": alert_id,
                "org_id": org_id,
                "task_id": task_id,
            },
        )
        return True
