import asyncio
from datetime import UTC, datetime

from app.worker import digest_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
USER_ID_1 = "11111111-1111-1111-1111-111111111112"
USER_ID_2 = "11111111-1111-1111-1111-111111111113"


def test_digest_processor_sends_digest_with_mocked_smtp_and_admin_lookup(monkeypatch) -> None:
    sent_emails: list[dict[str, str]] = []
    updated_timestamps: list[tuple[str, str]] = []
    audit_events: list[dict[str, object]] = []

    async def fake_list_rules(limit: int = 50):
        assert limit == 50
        return [
            {
                "org_id": ORG_ID,
                "enabled": True,
                "mode": "digest",
                "digest_cadence": "daily",
                "min_severity": "medium",
                "last_digest_sent_at": None,
            }
        ]

    async def fake_org_name(org_id: str) -> str:
        assert org_id == ORG_ID
        return "Acme"

    async def fake_member_ids(org_id: str) -> list[str]:
        assert org_id == ORG_ID
        return [USER_ID_1, USER_ID_2]

    async def fake_prefs(user_ids: list[str]) -> dict[str, bool]:
        assert user_ids == [USER_ID_1, USER_ID_2]
        return {USER_ID_1: True, USER_ID_2: False}

    async def fake_email_lookup(user_id: str, *, cache=None) -> str | None:
        assert user_id == USER_ID_1
        return "owner@example.com"

    async def fake_findings(access_token: str, org_id: str):
        assert access_token == "service-role-token"
        assert org_id == ORG_ID
        return [
            {"id": "finding-1", "severity": "high", "title": "Critical control gap"},
            {"id": "finding-2", "severity": "low", "title": "Minor policy typo"},
        ]

    async def fake_alerts(access_token: str, org_id: str):
        assert access_token == "service-role-token"
        assert org_id == ORG_ID
        return [
            {"id": "alert-1", "finding_id": "finding-1", "status": "open", "created_at": "2026-02-14T00:00:00Z"},
            {"id": "alert-2", "finding_id": "finding-2", "status": "open", "created_at": "2026-02-14T00:00:00Z"},
            {"id": "alert-3", "finding_id": "finding-1", "status": "resolved", "created_at": "2026-02-14T00:00:00Z"},
        ]

    async def fake_readiness(access_token: str, org_id: str):
        assert access_token == "service-role-token"
        assert org_id == ORG_ID
        return {"score": 77}

    async def fake_update_timestamp(org_id: str, sent_at: str) -> None:
        updated_timestamps.append((org_id, sent_at))

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "service-role-token"
        audit_events.append(payload)

    def fake_send_email(*, to: str, subject: str, html: str, text: str, request_id: str | None = None) -> None:
        sent_emails.append(
            {"to": to, "subject": subject, "html": html, "text": text, "request_id": request_id or ""}
        )

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(digest_processor, "list_digest_notification_rules_service", fake_list_rules)
    monkeypatch.setattr(digest_processor, "select_org_name_service", fake_org_name)
    monkeypatch.setattr(digest_processor, "select_org_member_user_ids_service", fake_member_ids)
    monkeypatch.setattr(digest_processor, "select_user_notification_prefs_for_users_service", fake_prefs)
    monkeypatch.setattr(digest_processor, "fetch_user_email_by_id", fake_email_lookup)
    monkeypatch.setattr(digest_processor, "select_findings", fake_findings)
    monkeypatch.setattr(digest_processor, "select_alerts", fake_alerts)
    monkeypatch.setattr(digest_processor, "get_latest_org_readiness", fake_readiness)
    monkeypatch.setattr(digest_processor, "update_org_notification_last_digest_sent_service", fake_update_timestamp)
    monkeypatch.setattr(digest_processor, "rpc_record_audit_event", fake_audit)
    monkeypatch.setattr(digest_processor, "send_email", fake_send_email)
    monkeypatch.setattr(digest_processor, "run_in_threadpool", fake_run_in_threadpool)

    processor = digest_processor.DigestProcessor(
        access_token="service-role-token",
        send_hour_utc=0,
        batch_limit=50,
        interval_seconds=60,
    )
    processed = asyncio.run(processor.process_if_due())

    assert processed == 1
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "owner@example.com"
    assert "Verirule digest: Acme" in sent_emails[0]["subject"]
    assert len(updated_timestamps) == 1
    assert updated_timestamps[0][0] == ORG_ID
    assert len(audit_events) == 1
    assert audit_events[0]["p_action"] == "digest_sent"


def test_digest_processor_skips_when_digest_already_sent_today(monkeypatch) -> None:
    now_iso = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    async def fake_list_rules(limit: int = 50):
        return [
            {
                "org_id": ORG_ID,
                "enabled": True,
                "mode": "digest",
                "digest_cadence": "daily",
                "min_severity": "medium",
                "last_digest_sent_at": now_iso,
            }
        ]

    async def fail_send(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("Digest should not send when already sent today")

    monkeypatch.setattr(digest_processor, "list_digest_notification_rules_service", fake_list_rules)
    monkeypatch.setattr(digest_processor.DigestProcessor, "_send_digest_for_org", fail_send)

    processor = digest_processor.DigestProcessor(
        access_token="service-role-token",
        send_hour_utc=0,
        batch_limit=50,
        interval_seconds=60,
    )
    processed = asyncio.run(processor.process_if_due())

    assert processed == 0
