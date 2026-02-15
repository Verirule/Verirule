from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.core.supabase_rest import (
    create_task_escalation_service,
    enqueue_notification_job,
    list_enabled_sla_rules_service,
    mark_task_escalation_notified_service,
    rpc_record_audit_event,
    select_integration_secret,
    select_open_tasks_for_sla_service,
    update_task_sla_state_service,
)
from app.worker.retry import sanitize_error

logger = get_logger("worker.sla")
TaskSlaState = Literal["on_track", "due_soon", "overdue"]


def _parse_utc_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _state_for_due_at(*, now: datetime, due_at: datetime, due_soon_threshold_hours: int) -> TaskSlaState:
    if now > due_at:
        return "overdue"
    if due_at - now <= timedelta(hours=max(1, due_soon_threshold_hours)):
        return "due_soon"
    return "on_track"


def _floor_hour(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0)


def _floor_interval_hours(now: datetime, interval_hours: int) -> datetime:
    interval_seconds = max(1, interval_hours) * 3600
    epoch = int(now.timestamp())
    floored = epoch - (epoch % interval_seconds)
    return datetime.fromtimestamp(floored, tz=UTC)


class SLAProcessor:
    def __init__(self, *, access_token: str, interval_seconds: int = 300, org_limit: int = 500) -> None:
        self.access_token = access_token
        self.interval_seconds = max(30, interval_seconds)
        self.org_limit = max(1, org_limit)
        self._next_run_at: datetime = datetime.now(UTC)

    def _is_due(self, now: datetime) -> bool:
        return now >= self._next_run_at

    async def process_if_due(self) -> int:
        now = datetime.now(UTC)
        if not self._is_due(now):
            return 0

        queued_count = 0
        try:
            rules_rows = await list_enabled_sla_rules_service(limit=self.org_limit)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "sla.rules_query_failed",
                extra={
                    "component": "worker",
                    "error": sanitize_error(exc, default_message="sla rules query failed"),
                },
            )
            self._next_run_at = now + timedelta(seconds=self.interval_seconds)
            return 0

        for row in rules_rows:
            org_id = row.get("org_id")
            if not isinstance(org_id, str) or not org_id.strip():
                continue
            try:
                queued_count += await self._process_org(org_id.strip(), row, now)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning(
                    "sla.org_process_failed",
                    extra={
                        "component": "worker",
                        "org_id": org_id,
                        "error": sanitize_error(exc, default_message="sla org process failed"),
                    },
                )

        self._next_run_at = now + timedelta(seconds=self.interval_seconds)
        return queued_count

    async def _process_org(self, org_id: str, rules: dict[str, Any], now: datetime) -> int:
        due_soon_threshold_hours = max(1, int(rules.get("due_soon_threshold_hours") or 12))
        overdue_remind_every_hours = max(1, int(rules.get("overdue_remind_every_hours") or 24))
        settings = get_settings()
        dashboard_url = f"{settings.NEXT_PUBLIC_SITE_URL.rstrip('/')}/dashboard/tasks?org_id={org_id}"

        slack_connected = False
        if settings.SLACK_ALERT_NOTIFICATIONS_ENABLED:
            integration = await select_integration_secret(self.access_token, org_id, "slack")
            slack_connected = (
                isinstance(integration, dict)
                and str(integration.get("status") or "").strip().lower() == "connected"
            )
        channel = "both" if slack_connected else "email"

        tasks = await select_open_tasks_for_sla_service(org_id)
        queued_count = 0
        for task in tasks:
            task_id = task.get("id")
            due_at_value = task.get("due_at")
            if not isinstance(task_id, str) or not task_id.strip():
                continue
            due_at = _parse_utc_timestamp(due_at_value)
            if due_at is None:
                continue

            next_state = _state_for_due_at(
                now=now,
                due_at=due_at,
                due_soon_threshold_hours=due_soon_threshold_hours,
            )
            current_state = str(task.get("sla_state") or "none").strip().lower()
            if current_state != next_state:
                await update_task_sla_state_service(task_id.strip(), next_state)

            if next_state == "on_track":
                continue

            kind = "overdue" if next_state == "overdue" else "due_soon"
            window_start_dt = (
                _floor_interval_hours(now, overdue_remind_every_hours)
                if kind == "overdue"
                else _floor_hour(now)
            )
            window_start = window_start_dt.isoformat().replace("+00:00", "Z")

            escalation = await create_task_escalation_service(
                org_id=org_id,
                task_id=task_id.strip(),
                kind=kind,
                window_start=window_start,
                channel=channel,
            )
            if not isinstance(escalation, dict):
                continue

            severity = str(task.get("severity") or "medium").strip().lower()
            if severity not in {"low", "medium", "high"}:
                severity = "medium"
            task_title = str(task.get("title") or "Untitled remediation task").strip() or "Untitled remediation task"
            due_at_text = due_at.isoformat().replace("+00:00", "Z")
            job = await enqueue_notification_job(
                org_id,
                "sla",
                {
                    "org_id": org_id,
                    "task_id": task_id.strip(),
                    "kind": kind,
                    "task_title": task_title,
                    "severity": severity,
                    "due_at": due_at_text,
                    "channel": channel,
                    "dashboard_url": dashboard_url,
                    "entity_type": "task",
                    "entity_id": task_id.strip(),
                },
            )
            if not isinstance(job, dict):
                continue

            escalation_id = escalation.get("id")
            if isinstance(escalation_id, str) and escalation_id.strip():
                await mark_task_escalation_notified_service(
                    escalation_id.strip(),
                    notification_job_id=str(job.get("id") or "").strip() or None,
                )

            await rpc_record_audit_event(
                self.access_token,
                {
                    "p_org_id": org_id,
                    "p_action": "sla_escalation_queued",
                    "p_entity_type": "notification_job",
                    "p_entity_id": job.get("id"),
                    "p_metadata": {
                        "task_id": task_id.strip(),
                        "kind": kind,
                        "channel": channel,
                        "window_start": window_start,
                    },
                },
            )
            queued_count += 1

        return queued_count
