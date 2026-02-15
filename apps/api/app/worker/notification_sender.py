from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi.concurrency import run_in_threadpool

from app.core.crypto import decrypt_json
from app.core.logging import get_logger
from app.core.settings import get_settings
from app.core.supabase_rest import (
    ensure_org_notification_rules,
    fetch_due_notification_jobs,
    get_org_notification_rules,
    list_org_member_emails,
    mark_notification_job_failed,
    mark_notification_job_running,
    mark_notification_job_sent,
    rpc_record_audit_event,
    select_alert_by_id_for_org,
    select_finding_by_id,
    select_integration_secret,
    select_org_name_service,
    select_user_notification_prefs_for_users_service,
    upsert_notification_event_service,
)
from app.integrations.slack import send_webhook
from app.notifications.emailer import EmailNotConfiguredError, EmailSendError, send_email
from app.notifications.templates import (
    digest_email,
    immediate_alert_email,
    sla_due_soon_email,
    sla_overdue_email,
)
from app.worker.retry import backoff_seconds, sanitize_error

logger = get_logger("worker.notification_sender")

_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def _severity_meets_minimum(*, severity: str, min_severity: str) -> bool:
    threshold = _SEVERITY_RANK.get(min_severity.strip().lower(), _SEVERITY_RANK["medium"])
    score = _SEVERITY_RANK.get(severity.strip().lower(), _SEVERITY_RANK["medium"])
    return score >= threshold


class NotificationSender:
    def __init__(
        self,
        *,
        access_token: str,
        batch_limit: int = 50,
        max_attempts: int = 5,
    ) -> None:
        self.access_token = access_token
        self.batch_limit = max(1, batch_limit)
        self.max_attempts = max(1, max_attempts)

    async def process_queued_jobs_once(self) -> int:
        jobs = await fetch_due_notification_jobs(limit=self.batch_limit)
        processed = 0
        for job in jobs:
            sent = await self._process_job(job)
            if sent:
                processed += 1
        return processed

    async def _process_job(self, job: dict[str, Any]) -> bool:
        job_id = str(job.get("id") or "").strip()
        org_id = str(job.get("org_id") or "").strip()
        job_type = str(job.get("type") or "").strip()
        payload = job.get("payload")
        if not job_id or not org_id or job_type not in {"digest", "immediate_alert", "sla"}:
            return False
        if not isinstance(payload, dict):
            payload = {}

        current_attempts = _safe_int(job.get("attempts"))
        next_attempt = current_attempts + 1
        await mark_notification_job_running(job_id, next_attempt)

        try:
            if job_type == "digest":
                delivered = await self._send_digest_job(
                    org_id,
                    job_id,
                    next_attempt,
                    payload,
                    request_id=f"notify-{job_id}",
                )
            elif job_type == "immediate_alert":
                delivered = await self._send_immediate_alert_job(
                    org_id,
                    job_id,
                    next_attempt,
                    payload,
                    request_id=f"notify-{job_id}",
                )
            else:
                delivered = await self._send_sla_job(
                    org_id,
                    job_id,
                    next_attempt,
                    payload,
                    request_id=f"notify-{job_id}",
                )

            await mark_notification_job_sent(job_id, next_attempt)
            await rpc_record_audit_event(
                self.access_token,
                {
                    "p_org_id": org_id,
                    "p_action": "email_sent",
                    "p_entity_type": "notification_job",
                    "p_entity_id": job_id,
                    "p_metadata": {
                        "type": job_type,
                        "count": delivered,
                    },
                },
            )
            return True
        except Exception as exc:
            error_text = sanitize_error(exc, default_message="notification job failed")
            if next_attempt >= self.max_attempts:
                await mark_notification_job_failed(
                    job_id,
                    next_attempt,
                    error_text,
                    terminal=True,
                )
            else:
                retry_at = (
                    datetime.now(UTC) + timedelta(seconds=backoff_seconds(next_attempt))
                ).isoformat().replace("+00:00", "Z")
                await mark_notification_job_failed(
                    job_id,
                    next_attempt,
                    error_text,
                    run_after=retry_at,
                    terminal=False,
                )
            logger.warning(
                "notification_sender.job_failed",
                extra={
                    "component": "worker",
                    "org_id": org_id,
                    "job_id": job_id,
                    "type": job_type,
                    "error": error_text,
                },
            )
            return False

    async def _send_digest_job(
        self,
        org_id: str,
        job_id: str,
        attempt: int,
        payload: dict[str, Any],
        *,
        request_id: str,
    ) -> int:
        org_name = str(payload.get("org_name") or "").strip() or (await select_org_name_service(org_id) or org_id)
        recipients = _normalized_recipient_targets(payload.get("recipient_targets"))
        if not recipients:
            recipients = await self._recipient_targets_from_emails(
                org_id,
                _normalized_recipients(payload.get("recipients")),
            )
        alerts = payload.get("alerts") if isinstance(payload.get("alerts"), list) else []
        findings = payload.get("findings") if isinstance(payload.get("findings"), dict) else {}
        readiness_summary = (
            payload.get("readiness_summary")
            if isinstance(payload.get("readiness_summary"), dict)
            else {}
        )
        dashboard_url = str(payload.get("dashboard_url") or "").strip()
        if not dashboard_url:
            settings = get_settings()
            dashboard_url = f"{settings.NEXT_PUBLIC_SITE_URL.rstrip('/')}/dashboard?org={org_id}"

        message = digest_email(
            org_name,
            alerts,
            _normalized_findings(findings),
            readiness_summary,
            dashboard_url,
        )
        return await self._send_message_to_recipients(
            org_id=org_id,
            job_id=job_id,
            attempt=attempt,
            job_type="digest",
            payload=payload,
            recipients=recipients,
            subject=message["subject"],
            html=message["html"],
            text=message["text"],
            request_id=request_id,
        )

    async def _send_immediate_alert_job(
        self,
        org_id: str,
        job_id: str,
        attempt: int,
        payload: dict[str, Any],
        *,
        request_id: str,
    ) -> int:
        alert_id = str(payload.get("alert_id") or "").strip()
        if not alert_id:
            raise ValueError("immediate alert payload missing alert_id")

        await ensure_org_notification_rules(self.access_token, org_id)
        rules = await get_org_notification_rules(self.access_token, org_id)
        if not isinstance(rules, dict):
            return 0
        if not bool(rules.get("enabled", True)):
            return 0
        mode = str(rules.get("mode") or "digest").strip().lower()
        if mode not in {"immediate", "both"}:
            return 0

        alert = await select_alert_by_id_for_org(self.access_token, org_id, alert_id)
        if not isinstance(alert, dict):
            return 0

        finding = None
        finding_id = alert.get("finding_id")
        if isinstance(finding_id, str) and finding_id.strip():
            finding = await select_finding_by_id(self.access_token, finding_id.strip())

        severity = str((finding or {}).get("severity") or "medium")
        min_severity = str(rules.get("min_severity") or "medium")
        if not _severity_meets_minimum(severity=severity, min_severity=min_severity):
            return 0

        recipients = await self._collect_recipients(org_id)
        if not recipients:
            return 0

        org_name = await select_org_name_service(org_id) or org_id
        settings = get_settings()
        dashboard_url = (
            f"{settings.NEXT_PUBLIC_SITE_URL.rstrip('/')}/dashboard?org={org_id}&alert={alert_id}"
        )
        message = immediate_alert_email(
            org_name,
            {
                "severity": severity,
                "title": (finding or {}).get("title") or "New high-severity alert",
            },
            dashboard_url,
        )
        return await self._send_message_to_recipients(
            org_id=org_id,
            job_id=job_id,
            attempt=attempt,
            job_type="immediate_alert",
            payload=payload,
            recipients=recipients,
            subject=message["subject"],
            html=message["html"],
            text=message["text"],
            request_id=request_id,
        )

    async def _send_sla_job(
        self,
        org_id: str,
        job_id: str,
        attempt: int,
        payload: dict[str, Any],
        *,
        request_id: str,
    ) -> int:
        kind = str(payload.get("kind") or "").strip().lower()
        if kind not in {"due_soon", "overdue"}:
            raise ValueError("sla payload missing kind")

        task_id = _as_uuid_string(payload.get("task_id"))
        if not task_id:
            raise ValueError("sla payload missing task_id")

        task_title = str(payload.get("task_title") or payload.get("title") or "").strip()
        if not task_title:
            task_title = "Untitled remediation task"
        severity = str(payload.get("severity") or "medium").strip().lower()
        due_at = str(payload.get("due_at") or "").strip() or "Unknown"

        org_name = await select_org_name_service(org_id) or org_id
        settings = get_settings()
        dashboard_url = str(payload.get("dashboard_url") or "").strip()
        if not dashboard_url:
            dashboard_url = f"{settings.NEXT_PUBLIC_SITE_URL.rstrip('/')}/dashboard/tasks?org_id={org_id}"

        message = (
            sla_overdue_email(
                org_name,
                {"title": task_title, "severity": severity, "due_at": due_at},
                dashboard_url,
            )
            if kind == "overdue"
            else sla_due_soon_email(
                org_name,
                {"title": task_title, "severity": severity, "due_at": due_at},
                dashboard_url,
            )
        )

        channel = str(payload.get("channel") or "email").strip().lower()
        if channel not in {"email", "slack", "both"}:
            channel = "email"

        delivered = 0
        if channel in {"email", "both"}:
            recipients = await self._collect_recipients(org_id)
            if recipients:
                delivered = await self._send_message_to_recipients(
                    org_id=org_id,
                    job_id=job_id,
                    attempt=attempt,
                    job_type="sla",
                    payload=payload,
                    recipients=recipients,
                    subject=message["subject"],
                    html=message["html"],
                    text=message["text"],
                    request_id=request_id,
                )

        if channel in {"slack", "both"}:
            try:
                await self._send_sla_slack_notification(
                    org_id=org_id,
                    task_id=task_id,
                    task_title=task_title,
                    severity=severity,
                    due_at=due_at,
                    kind=kind,
                    dashboard_url=dashboard_url,
                )
            except Exception as exc:  # pragma: no cover - best effort
                logger.warning(
                    "notification_sender.sla_slack_failed",
                    extra={
                        "component": "worker",
                        "org_id": org_id,
                        "task_id": task_id,
                        "error": sanitize_error(
                            exc,
                            default_message="sla slack delivery failed",
                        ),
                    },
                )

        return delivered

    async def _send_sla_slack_notification(
        self,
        *,
        org_id: str,
        task_id: str,
        task_title: str,
        severity: str,
        due_at: str,
        kind: str,
        dashboard_url: str,
    ) -> None:
        settings = get_settings()
        if not settings.SLACK_ALERT_NOTIFICATIONS_ENABLED:
            return

        row = await select_integration_secret(self.access_token, org_id, "slack")
        if not isinstance(row, dict):
            return
        if str(row.get("status") or "").strip().lower() != "connected":
            return

        ciphertext = row.get("secret_ciphertext")
        if not isinstance(ciphertext, str) or not ciphertext.strip():
            return

        secret = decrypt_json(ciphertext.strip())
        webhook_url = secret.get("webhook_url")
        if not isinstance(webhook_url, str) or not webhook_url.strip():
            return

        state_text = "overdue" if kind == "overdue" else "due soon"
        text = (
            f"Verirule SLA escalation ({state_text})\n"
            f"Task: {task_title}\n"
            f"Severity: {severity.upper()}\n"
            f"Due at: {due_at}\n"
            f"Task ID: {task_id}\n"
            f"Task list: {dashboard_url}"
        )
        await send_webhook(webhook_url.strip(), {"text": text})

    async def _collect_recipients(self, org_id: str) -> list[dict[str, str]]:
        member_rows = await list_org_member_emails(org_id)
        user_ids: list[str] = []
        for row in member_rows:
            user_id = row.get("user_id")
            if isinstance(user_id, str) and user_id.strip():
                user_ids.append(user_id.strip())

        prefs = await select_user_notification_prefs_for_users_service(user_ids)
        recipients: list[dict[str, str]] = []
        for row in member_rows:
            user_id = row.get("user_id")
            email = row.get("user_email")
            if not isinstance(user_id, str) or not user_id.strip():
                continue
            if not isinstance(email, str) or not email.strip():
                continue
            if not prefs.get(user_id.strip(), True):
                continue
            recipients.append({"user_id": user_id.strip(), "email": email.strip().lower()})
        return _dedupe_recipient_targets(recipients)

    async def _recipient_targets_from_emails(
        self,
        org_id: str,
        emails: list[str],
    ) -> list[dict[str, str]]:
        if not emails:
            return []
        email_set = {email.strip().lower() for email in emails if email.strip()}
        if not email_set:
            return []

        member_rows = await list_org_member_emails(org_id)
        targets: list[dict[str, str]] = []
        for row in member_rows:
            user_id = row.get("user_id")
            email = row.get("user_email")
            if not isinstance(user_id, str) or not user_id.strip():
                continue
            if not isinstance(email, str) or not email.strip():
                continue
            normalized = email.strip().lower()
            if normalized not in email_set:
                continue
            targets.append({"user_id": user_id.strip(), "email": normalized})
        return _dedupe_recipient_targets(targets)

    async def _send_message_to_recipients(
        self,
        *,
        org_id: str,
        job_id: str,
        attempt: int,
        job_type: str,
        payload: dict[str, Any],
        recipients: list[dict[str, str]],
        subject: str,
        html: str,
        text: str,
        request_id: str,
    ) -> int:
        delivered = 0
        entity_type, entity_id = _event_ref(job_type, payload)
        for recipient in recipients:
            recipient_email = recipient.get("email")
            recipient_user_id = recipient.get("user_id")
            if not isinstance(recipient_email, str) or not recipient_email.strip():
                continue
            if not isinstance(recipient_user_id, str) or not recipient_user_id.strip():
                continue

            await upsert_notification_event_service(
                org_id=org_id,
                user_id=recipient_user_id.strip(),
                job_id=job_id,
                event_type=job_type,
                entity_type=entity_type,
                entity_id=entity_id,
                subject=subject,
                status_value="queued",
                attempts=attempt,
                last_error=None,
                sent_at=None,
            )
            try:
                await run_in_threadpool(
                    send_email,
                    to=recipient_email.strip().lower(),
                    subject=subject,
                    html=html,
                    text=text,
                    request_id=request_id,
                )
                await upsert_notification_event_service(
                    org_id=org_id,
                    user_id=recipient_user_id.strip(),
                    job_id=job_id,
                    event_type=job_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    subject=subject,
                    status_value="sent",
                    attempts=attempt,
                    last_error=None,
                    sent_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                )
                delivered += 1
            except (EmailNotConfiguredError, EmailSendError) as exc:
                await upsert_notification_event_service(
                    org_id=org_id,
                    user_id=recipient_user_id.strip(),
                    job_id=job_id,
                    event_type=job_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    subject=subject,
                    status_value="failed",
                    attempts=attempt,
                    last_error=sanitize_error(exc, default_message="email delivery failed"),
                    sent_at=None,
                )
                raise
        return delivered


def _safe_int(value: object | None) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _normalized_recipients(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    recipients: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            recipients.append(item.strip().lower())
    return sorted(set(recipients))


def _normalized_recipient_targets(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    recipients: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        user_id = item.get("user_id")
        email = item.get("email")
        if not isinstance(user_id, str) or not user_id.strip():
            continue
        if not isinstance(email, str) or not email.strip():
            continue
        recipients.append({"user_id": user_id.strip(), "email": email.strip().lower()})
    return _dedupe_recipient_targets(recipients)


def _dedupe_recipient_targets(value: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for row in sorted(value, key=lambda item: (item["email"], item["user_id"])):
        email = row["email"]
        if email in seen:
            continue
        seen.add(email)
        deduped.append(row)
    return deduped


def _event_ref(job_type: str, payload: dict[str, Any]) -> tuple[str | None, str | None]:
    entity_type = str(payload.get("entity_type") or "").strip().lower()
    if not entity_type:
        if job_type == "immediate_alert":
            entity_type = "alert"
        elif job_type == "sla":
            entity_type = "task"
        else:
            entity_type = "system"
    if entity_type not in {"alert", "task", "export", "system"}:
        entity_type = "system"

    candidate_entity_id = payload.get("entity_id")
    if not isinstance(candidate_entity_id, str) or not candidate_entity_id.strip():
        if job_type == "immediate_alert":
            candidate_entity_id = payload.get("alert_id")
        elif job_type == "sla":
            candidate_entity_id = payload.get("task_id")

    entity_id = _as_uuid_string(candidate_entity_id)
    return entity_type, entity_id


def _as_uuid_string(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        return str(UUID(text))
    except ValueError:
        return None


def _normalized_findings(value: dict[str, Any]) -> dict[str, int]:
    open_alerts = _safe_int(value.get("open_alerts"))
    findings_total = _safe_int(value.get("findings_total"))
    return {
        "open_alerts": max(0, open_alerts),
        "findings_total": max(0, findings_total),
    }
