from app.notifications.templates import (
    digest_email,
    immediate_alert_email,
    sla_due_soon_email,
    sla_overdue_email,
)


def test_digest_email_renders_subject_and_summary() -> None:
    payload = digest_email(
        "Acme",
        alerts=[
            {"severity": "high", "title": "Policy change in data retention"},
            {"severity": "medium", "title": "Vendor terms updated"},
        ],
        findings={"open_alerts": 2, "findings_total": 5},
        readiness_summary={"score": 81},
        dashboard_url="https://app.verirule.com/dashboard",
    )

    assert payload["subject"] == "Verirule digest: Acme"
    assert "Open alerts: 2" in payload["text"]
    assert "Readiness score: 81/100" in payload["text"]
    assert "Policy change in data retention" in payload["html"]


def test_immediate_alert_email_renders_core_fields() -> None:
    payload = immediate_alert_email(
        "Acme",
        {
            "severity": "high",
            "title": "Critical control gap detected",
        },
        "https://app.verirule.com/dashboard",
    )

    assert payload["subject"] == "Verirule alert (HIGH): Acme"
    assert "Critical control gap detected" in payload["text"]
    assert "https://app.verirule.com/dashboard" in payload["html"]


def test_sla_due_soon_email_renders_core_fields() -> None:
    payload = sla_due_soon_email(
        "Acme",
        {"title": "Rotate access keys", "severity": "high", "due_at": "2026-02-16T12:00:00Z"},
        "https://app.verirule.com/dashboard/tasks?org_id=1",
    )

    assert payload["subject"] == "Action required: Task due soon - Rotate access keys"
    assert "Rotate access keys" in payload["text"]
    assert "2026-02-16T12:00:00Z" in payload["html"]


def test_sla_overdue_email_renders_core_fields() -> None:
    payload = sla_overdue_email(
        "Acme",
        {"title": "Close exposed S3 bucket", "severity": "medium", "due_at": "2026-02-14T10:00:00Z"},
        "https://app.verirule.com/dashboard/tasks?org_id=1",
    )

    assert payload["subject"] == "Overdue: Remediation task past due - Close exposed S3 bucket"
    assert "Close exposed S3 bucket" in payload["text"]
    assert "2026-02-14T10:00:00Z" in payload["html"]
