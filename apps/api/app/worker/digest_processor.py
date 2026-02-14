from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi.concurrency import run_in_threadpool

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.core.supabase_admin_auth import fetch_user_email_by_id
from app.core.supabase_rest import (
    get_latest_org_readiness,
    list_digest_notification_rules_service,
    rpc_record_audit_event,
    select_alerts,
    select_findings,
    select_org_member_user_ids_service,
    select_org_name_service,
    select_user_notification_prefs_for_users_service,
    update_org_notification_last_digest_sent_service,
)
from app.notifications.emailer import EmailNotConfiguredError, EmailSendError, send_email
from app.notifications.templates import digest_email
from app.worker.retry import sanitize_error

logger = get_logger("worker.digest")

_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def _parse_utc_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _cutoff_today(now: datetime, send_hour_utc: int) -> datetime:
    hour = max(0, min(send_hour_utc, 23))
    return now.replace(hour=hour, minute=0, second=0, microsecond=0)


def _week_start(current_date: date) -> date:
    return current_date - timedelta(days=current_date.weekday())


def _severity_meets_minimum(*, severity: str, min_severity: str) -> bool:
    threshold = _SEVERITY_RANK.get(min_severity.strip().lower(), _SEVERITY_RANK["medium"])
    score = _SEVERITY_RANK.get(severity.strip().lower(), _SEVERITY_RANK["medium"])
    return score >= threshold


def _is_digest_due(rule: dict[str, Any], now: datetime, send_hour_utc: int) -> bool:
    enabled = bool(rule.get("enabled", True))
    if not enabled:
        return False

    mode = str(rule.get("mode") or "digest").strip().lower()
    if mode not in {"digest", "both"}:
        return False

    cadence = str(rule.get("digest_cadence") or "daily").strip().lower()
    cutoff = _cutoff_today(now, send_hour_utc)
    if now < cutoff:
        return False

    last_sent = _parse_utc_timestamp(rule.get("last_digest_sent_at"))
    if cadence == "weekly":
        if now.weekday() != 0:
            return False
        week_start = _week_start(now.date())
        if last_sent is None:
            return True
        return _week_start(last_sent.date()) < week_start

    if last_sent is None:
        return True
    return last_sent.date() < now.date()


class DigestProcessor:
    def __init__(
        self,
        *,
        access_token: str,
        send_hour_utc: int = 8,
        batch_limit: int = 50,
        interval_seconds: int = 300,
    ) -> None:
        self.access_token = access_token
        self.send_hour_utc = max(0, min(send_hour_utc, 23))
        self.batch_limit = max(1, batch_limit)
        self.interval_seconds = max(30, interval_seconds)
        self._next_run_at: datetime = datetime.now(UTC)

    def _scan_due(self, now: datetime) -> bool:
        return now >= self._next_run_at

    async def process_if_due(self) -> int:
        now = datetime.now(UTC)
        if not self._scan_due(now):
            return 0

        sent_count = 0
        email_cache: dict[str, str | None] = {}

        try:
            rules = await list_digest_notification_rules_service(limit=self.batch_limit)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "digest.rules_query_failed",
                extra={
                    "component": "worker",
                    "error": sanitize_error(exc, default_message="digest rules query failed"),
                },
            )
            self._next_run_at = now + timedelta(seconds=self.interval_seconds)
            return 0

        for rule in rules:
            org_id = rule.get("org_id")
            if not isinstance(org_id, str) or not org_id.strip():
                continue
            if not _is_digest_due(rule, now, self.send_hour_utc):
                continue

            try:
                sent = await self._send_digest_for_org(org_id.strip(), rule, now, email_cache=email_cache)
                if sent:
                    sent_count += 1
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning(
                    "digest.org_send_failed",
                    extra={
                        "component": "worker",
                        "org_id": org_id,
                        "error": sanitize_error(exc, default_message="digest send failed"),
                    },
                )

        self._next_run_at = now + timedelta(seconds=self.interval_seconds)
        return sent_count

    async def _send_digest_for_org(
        self,
        org_id: str,
        rule: dict[str, Any],
        now: datetime,
        *,
        email_cache: dict[str, str | None],
    ) -> bool:
        org_name = await select_org_name_service(org_id) or org_id
        recipients = await self._collect_recipients(org_id, email_cache=email_cache)
        request_id = f"digest-{org_id}-{now.date().isoformat()}"

        findings = await select_findings(self.access_token, org_id)
        findings_by_id: dict[str, dict[str, Any]] = {}
        for finding in findings:
            finding_id = finding.get("id")
            if isinstance(finding_id, str) and finding_id.strip():
                findings_by_id[finding_id] = finding

        min_severity = str(rule.get("min_severity") or "medium")
        alerts = await select_alerts(self.access_token, org_id)
        digest_alerts: list[dict[str, Any]] = []
        open_alerts = 0
        for alert in alerts:
            if str(alert.get("status") or "").strip().lower() != "open":
                continue
            finding_id = alert.get("finding_id")
            finding = findings_by_id.get(finding_id) if isinstance(finding_id, str) else None
            severity = str((finding or {}).get("severity") or "medium")
            if not _severity_meets_minimum(severity=severity, min_severity=min_severity):
                continue
            open_alerts += 1
            digest_alerts.append(
                {
                    "id": alert.get("id"),
                    "severity": severity,
                    "title": (finding or {}).get("title") or "Untitled finding",
                    "created_at": alert.get("created_at"),
                }
            )

        readiness = await get_latest_org_readiness(self.access_token, org_id)
        settings = get_settings()
        dashboard_url = f"{settings.NEXT_PUBLIC_SITE_URL.rstrip('/')}/dashboard?org={org_id}"

        message = digest_email(
            org_name,
            digest_alerts,
            {
                "open_alerts": open_alerts,
                "findings_total": len(findings),
            },
            {
                "score": readiness.get("score") if isinstance(readiness, dict) else None,
                "dashboard_url": dashboard_url,
            },
        )

        delivered_count = 0
        for recipient in recipients:
            try:
                await run_in_threadpool(
                    send_email,
                    to=recipient,
                    subject=message["subject"],
                    html=message["html"],
                    text=message["text"],
                    request_id=request_id,
                )
                delivered_count += 1
            except (EmailNotConfiguredError, EmailSendError) as exc:
                logger.warning(
                    "digest.email_delivery_failed",
                    extra={
                        "component": "worker",
                        "org_id": org_id,
                        "request_id": request_id,
                        "error": sanitize_error(exc, default_message="email delivery failed"),
                    },
                )

        if delivered_count == 0 and recipients:
            return False

        sent_at = now.isoformat().replace("+00:00", "Z")
        await update_org_notification_last_digest_sent_service(org_id, sent_at)
        await rpc_record_audit_event(
            self.access_token,
            {
                "p_org_id": org_id,
                "p_action": "digest_sent",
                "p_entity_type": "notification_digest",
                "p_entity_id": None,
                "p_metadata": {
                    "count": delivered_count,
                    "mode": rule.get("mode"),
                    "digest_cadence": rule.get("digest_cadence"),
                    "min_severity": min_severity,
                },
            },
        )
        return True

    async def _collect_recipients(
        self, org_id: str, *, email_cache: dict[str, str | None]
    ) -> list[str]:
        user_ids = await select_org_member_user_ids_service(org_id)
        prefs = await select_user_notification_prefs_for_users_service(user_ids)
        recipients: list[str] = []
        for user_id in user_ids:
            email_enabled = prefs.get(user_id, True)
            if not email_enabled:
                continue
            email = await fetch_user_email_by_id(user_id, cache=email_cache)
            if isinstance(email, str) and email.strip():
                recipients.append(email.strip().lower())
        return sorted(set(recipients))

