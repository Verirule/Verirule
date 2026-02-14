from app.notifications.templates import digest_email, immediate_alert_email


def test_digest_email_renders_subject_and_summary() -> None:
    payload = digest_email(
        "Acme",
        alerts=[
            {"severity": "high", "title": "Policy change in data retention"},
            {"severity": "medium", "title": "Vendor terms updated"},
        ],
        findings={"open_alerts": 2, "findings_total": 5},
        readiness_summary={"score": 81, "dashboard_url": "https://app.verirule.com/dashboard"},
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
            "dashboard_url": "https://app.verirule.com/dashboard",
        },
    )

    assert payload["subject"] == "Verirule alert (HIGH): Acme"
    assert "Critical control gap detected" in payload["text"]
    assert "https://app.verirule.com/dashboard" in payload["html"]

