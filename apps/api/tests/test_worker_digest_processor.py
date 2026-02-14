import asyncio
from datetime import UTC, datetime

from app.worker import digest_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
USER_ID_1 = "11111111-1111-1111-1111-111111111112"
USER_ID_2 = "11111111-1111-1111-1111-111111111113"


def test_digest_processor_queues_digest_job(monkeypatch) -> None:
    queued_jobs: list[dict[str, object]] = []
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

    async def fake_member_emails(org_id: str):
        assert org_id == ORG_ID
        return [
            {"user_id": USER_ID_1, "user_email": "owner@example.com"},
            {"user_id": USER_ID_2, "user_email": "member@example.com"},
        ]

    async def fake_prefs(user_ids: list[str]) -> dict[str, bool]:
        assert user_ids == [USER_ID_1, USER_ID_2]
        return {USER_ID_1: True, USER_ID_2: False}

    async def fake_org_name(org_id: str) -> str:
        assert org_id == ORG_ID
        return "Acme"

    async def fake_findings(access_token: str, org_id: str):
        assert access_token == "service-role-token"
        assert org_id == ORG_ID
        return [
            {"id": "finding-1", "severity": "high", "title": "Critical control gap"},
            {"id": "finding-2", "severity": "low", "title": "Minor typo"},
        ]

    async def fake_alerts(access_token: str, org_id: str):
        assert access_token == "service-role-token"
        assert org_id == ORG_ID
        return [
            {"id": "alert-1", "finding_id": "finding-1", "status": "open", "created_at": "2026-02-14T00:00:00Z"},
            {"id": "alert-2", "finding_id": "finding-2", "status": "open", "created_at": "2026-02-14T00:00:00Z"},
        ]

    async def fake_readiness(access_token: str, org_id: str):
        assert access_token == "service-role-token"
        assert org_id == ORG_ID
        return {"score": 77}

    async def fake_enqueue(org_id: str, job_type: str, payload: dict[str, object], *, run_after: str | None = None):
        assert org_id == ORG_ID
        assert job_type == "digest"
        assert run_after is None
        queued_jobs.append(payload)
        return {"id": "job-1"}

    async def fake_update_timestamp(org_id: str, sent_at: str) -> None:
        updated_timestamps.append((org_id, sent_at))

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "service-role-token"
        audit_events.append(payload)

    monkeypatch.setattr(digest_processor, "list_digest_notification_rules_service", fake_list_rules)
    monkeypatch.setattr(digest_processor, "list_org_member_emails", fake_member_emails)
    monkeypatch.setattr(digest_processor, "select_user_notification_prefs_for_users_service", fake_prefs)
    monkeypatch.setattr(digest_processor, "select_org_name_service", fake_org_name)
    monkeypatch.setattr(digest_processor, "select_findings", fake_findings)
    monkeypatch.setattr(digest_processor, "select_alerts", fake_alerts)
    monkeypatch.setattr(digest_processor, "get_latest_org_readiness", fake_readiness)
    monkeypatch.setattr(digest_processor, "enqueue_notification_job", fake_enqueue)
    monkeypatch.setattr(digest_processor, "update_org_notification_last_digest_sent_service", fake_update_timestamp)
    monkeypatch.setattr(digest_processor, "rpc_record_audit_event", fake_audit)

    processor = digest_processor.DigestProcessor(
        access_token="service-role-token",
        send_hour_utc=0,
        batch_limit=50,
        interval_seconds=60,
    )
    processed = asyncio.run(processor.process_if_due())

    assert processed == 1
    assert len(queued_jobs) == 1
    assert queued_jobs[0]["org_id"] == ORG_ID
    assert queued_jobs[0]["org_name"] == "Acme"
    assert queued_jobs[0]["recipients"] == ["owner@example.com"]
    assert len(updated_timestamps) == 1
    assert updated_timestamps[0][0] == ORG_ID
    assert len(audit_events) == 1
    assert audit_events[0]["p_action"] == "digest_queued"


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

    async def fail_queue(self, *args, **kwargs):  # pragma: no cover
        raise AssertionError("Digest should not queue when already sent today")

    monkeypatch.setattr(digest_processor, "list_digest_notification_rules_service", fake_list_rules)
    monkeypatch.setattr(digest_processor.DigestProcessor, "_queue_digest_for_org", fail_queue)

    processor = digest_processor.DigestProcessor(
        access_token="service-role-token",
        send_hour_utc=0,
        batch_limit=50,
        interval_seconds=60,
    )
    processed = asyncio.run(processor.process_if_due())

    assert processed == 0
