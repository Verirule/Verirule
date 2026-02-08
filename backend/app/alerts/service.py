from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Iterable

from supabase import Client

from ..billing.limits import alert_limit_for_user
from ..config import Settings
from ..supabase_client import get_supabase_service_client

logger = logging.getLogger(__name__)


def _email_configured(settings: Settings) -> bool:
    return (
        settings.EMAIL_PROVIDER.lower() == "smtp"
        and settings.SMTP_HOST
        and settings.SMTP_PORT
        and settings.SMTP_FROM
    )


def _send_email(settings: Settings, to_email: str, subject: str, body: str) -> None:
    if not _email_configured(settings):
        logger.info("Email provider not configured; skipping send")
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
    except Exception as exc:
        logger.warning("Email send failed: %s", exc)


def _get_user_email(client: Client, user_id: str) -> str | None:
    try:
        result = client.auth.admin.get_user_by_id(user_id)
        user = getattr(result, "user", None) or result.get("user")
        if user and isinstance(user, dict):
            return user.get("email")
        if user:
            return getattr(user, "email", None)
    except Exception as exc:
        logger.warning("Failed to fetch user email: %s", exc)
    return None


def _existing_alert(client: Client, user_id: str, violation_id: str) -> bool:
    result = (
        client.table("alerts")
        .select("id")
        .eq("user_id", user_id)
        .eq("violation_id", violation_id)
        .limit(1)
        .execute()
    )
    return bool(result.data)


def _count_alerts(client: Client, user_id: str) -> int:
    result = (
        client.table("alerts").select("id").eq("user_id", user_id).execute()
    )
    return len(result.data or [])


def generate_alert_for_violation(
    settings: Settings,
    violation: Dict[str, Any],
    business_name: str,
    regulation_title: str,
    user_id: str,
    client: Client | None = None,
) -> Dict[str, Any] | None:
    """Create an alert for a violation if one does not already exist."""
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for alert generation")

    if client is None:
        client = get_supabase_service_client(settings)

    violation_id = violation.get("id")
    if not violation_id:
        return None

    if _existing_alert(client, user_id, violation_id):
        return None

    max_alerts = alert_limit_for_user(client, user_id)
    if _count_alerts(client, user_id) >= max_alerts:
        logger.info("Alert limit reached for user_id=%s", user_id)
        return None

    payload = {
        "user_id": user_id,
        "business_id": violation.get("business_id"),
        "violation_id": violation_id,
        "severity": violation.get("severity", "medium"),
        "title": f"Compliance alert: {regulation_title}",
        "message": violation.get("message", "Regulation violation detected."),
        "acknowledged": False,
    }

    result = client.table("alerts").insert(payload).execute()
    if not result.data:
        logger.warning("Alert insert failed for violation_id=%s", violation_id)
        return None

    if settings.DASHBOARD_URL:
        dashboard_line = f"Dashboard: {settings.DASHBOARD_URL}"
    else:
        dashboard_line = ""

    email = _get_user_email(client, user_id)
    if email:
        subject = f"Verirule alert - {payload['severity'].capitalize()} severity"
        body = "\n".join(
            [
                f"Business: {business_name}",
                f"Regulation: {regulation_title}",
                f"Severity: {payload['severity']}",
                payload["message"],
                dashboard_line,
            ]
        ).strip()
        _send_email(settings, email, subject, body)

    return result.data[0]


def generate_alerts_for_violations(
    settings: Settings,
    violations: Iterable[Dict[str, Any]],
    business_name: str,
    regulation_titles: Dict[str, str],
    user_id: str,
    client: Client | None = None,
) -> int:
    """Generate alerts for a list of violations. Returns count created."""
    created = 0
    for violation in violations:
        result = generate_alert_for_violation(
            settings,
            violation,
            business_name,
            regulation_titles.get(violation.get("regulation_id"), "Regulation"),
            user_id,
            client=client,
        )
        if result:
            created += 1
    return created
