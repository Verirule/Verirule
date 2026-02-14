import asyncio

from app.notifications.emailer import EmailSendError
from app.worker import notification_sender

ORG_ID = "11111111-1111-1111-1111-111111111111"


def test_notification_sender_sends_digest_job(monkeypatch) -> None:
    running_calls: list[tuple[str, int]] = []
    sent_calls: list[tuple[str, int]] = []
    failed_calls: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    sent_messages: list[dict[str, str]] = []
    audit_events: list[dict[str, object]] = []

    async def fake_fetch_due(limit: int = 50):
        assert limit == 50
        return [
            {
                "id": "job-1",
                "org_id": ORG_ID,
                "type": "digest",
                "payload": {
                    "org_name": "Acme",
                    "recipients": ["owner@example.com"],
                    "recipient_targets": [
                        {"user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "email": "owner@example.com"}
                    ],
                    "alerts": [{"severity": "high", "title": "Critical gap"}],
                    "findings": {"open_alerts": 1, "findings_total": 2},
                    "readiness_summary": {"score": 83},
                    "dashboard_url": "https://app.verirule.com/dashboard",
                },
                "attempts": 0,
            }
        ]

    async def fake_mark_running(job_id: str, attempts: int) -> None:
        running_calls.append((job_id, attempts))

    async def fake_mark_sent(job_id: str, attempts: int) -> None:
        sent_calls.append((job_id, attempts))

    async def fake_mark_failed(
        job_id: str,
        attempts: int,
        last_error: str | None,
        *,
        run_after: str | None = None,
        terminal: bool = False,
    ) -> None:
        failed_calls.append(
            {
                "job_id": job_id,
                "attempts": attempts,
                "last_error": last_error,
                "run_after": run_after,
                "terminal": terminal,
            }
        )

    def fake_send_email(*, to: str, subject: str, html: str, text: str, request_id: str | None = None) -> None:
        sent_messages.append(
            {
                "to": to,
                "subject": subject,
                "html": html,
                "text": text,
                "request_id": request_id or "",
            }
        )

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "service-role-token"
        audit_events.append(payload)

    async def fake_upsert_event(**kwargs):
        event_rows.append(kwargs)
        return {"id": "event-1"}

    monkeypatch.setattr(notification_sender, "fetch_due_notification_jobs", fake_fetch_due)
    monkeypatch.setattr(notification_sender, "mark_notification_job_running", fake_mark_running)
    monkeypatch.setattr(notification_sender, "mark_notification_job_sent", fake_mark_sent)
    monkeypatch.setattr(notification_sender, "mark_notification_job_failed", fake_mark_failed)
    monkeypatch.setattr(notification_sender, "send_email", fake_send_email)
    monkeypatch.setattr(notification_sender, "run_in_threadpool", fake_run_in_threadpool)
    monkeypatch.setattr(notification_sender, "rpc_record_audit_event", fake_audit)
    monkeypatch.setattr(notification_sender, "upsert_notification_event_service", fake_upsert_event)

    sender = notification_sender.NotificationSender(
        access_token="service-role-token",
        batch_limit=50,
        max_attempts=5,
    )
    processed = asyncio.run(sender.process_queued_jobs_once())

    assert processed == 1
    assert running_calls == [("job-1", 1)]
    assert sent_calls == [("job-1", 1)]
    assert failed_calls == []
    assert len(sent_messages) == 1
    assert sent_messages[0]["to"] == "owner@example.com"
    assert len(audit_events) == 1
    assert audit_events[0]["p_action"] == "email_sent"
    assert [row["status_value"] for row in event_rows] == ["queued", "sent"]


def test_notification_sender_retries_on_email_failure(monkeypatch) -> None:
    running_calls: list[tuple[str, int]] = []
    sent_calls: list[tuple[str, int]] = []
    failed_calls: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []

    async def fake_fetch_due(limit: int = 50):
        return [
            {
                "id": "job-2",
                "org_id": ORG_ID,
                "type": "digest",
                "payload": {
                    "org_name": "Acme",
                    "recipients": ["owner@example.com"],
                    "recipient_targets": [
                        {"user_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "email": "owner@example.com"}
                    ],
                    "alerts": [],
                    "findings": {"open_alerts": 0, "findings_total": 0},
                    "readiness_summary": {"score": 50},
                    "dashboard_url": "https://app.verirule.com/dashboard",
                },
                "attempts": 0,
            }
        ]

    async def fake_mark_running(job_id: str, attempts: int) -> None:
        running_calls.append((job_id, attempts))

    async def fake_mark_sent(job_id: str, attempts: int) -> None:
        sent_calls.append((job_id, attempts))

    async def fake_mark_failed(
        job_id: str,
        attempts: int,
        last_error: str | None,
        *,
        run_after: str | None = None,
        terminal: bool = False,
    ) -> None:
        failed_calls.append(
            {
                "job_id": job_id,
                "attempts": attempts,
                "last_error": last_error,
                "run_after": run_after,
                "terminal": terminal,
            }
        )

    def fake_send_email(*, to: str, subject: str, html: str, text: str, request_id: str | None = None) -> None:
        raise EmailSendError("smtp failure")

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    async def fake_upsert_event(**kwargs):
        event_rows.append(kwargs)
        return {"id": "event-2"}

    monkeypatch.setattr(notification_sender, "fetch_due_notification_jobs", fake_fetch_due)
    monkeypatch.setattr(notification_sender, "mark_notification_job_running", fake_mark_running)
    monkeypatch.setattr(notification_sender, "mark_notification_job_sent", fake_mark_sent)
    monkeypatch.setattr(notification_sender, "mark_notification_job_failed", fake_mark_failed)
    monkeypatch.setattr(notification_sender, "send_email", fake_send_email)
    monkeypatch.setattr(notification_sender, "run_in_threadpool", fake_run_in_threadpool)
    monkeypatch.setattr(notification_sender, "upsert_notification_event_service", fake_upsert_event)

    sender = notification_sender.NotificationSender(
        access_token="service-role-token",
        batch_limit=50,
        max_attempts=5,
    )
    processed = asyncio.run(sender.process_queued_jobs_once())

    assert processed == 0
    assert running_calls == [("job-2", 1)]
    assert sent_calls == []
    assert len(failed_calls) == 1
    assert failed_calls[0]["job_id"] == "job-2"
    assert failed_calls[0]["attempts"] == 1
    assert failed_calls[0]["terminal"] is False
    assert isinstance(failed_calls[0]["run_after"], str)
    assert [row["status_value"] for row in event_rows] == ["queued", "failed"]
