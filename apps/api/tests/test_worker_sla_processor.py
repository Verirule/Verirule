import asyncio
from datetime import UTC, datetime

from app.worker import sla_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
TASK_A = "22222222-2222-2222-2222-222222222222"
TASK_B = "33333333-3333-3333-3333-333333333333"


def test_sla_processor_queues_due_soon_and_overdue(monkeypatch) -> None:
    escalations: list[dict[str, object]] = []
    jobs: list[dict[str, object]] = []
    state_updates: list[tuple[str, str]] = []
    marked: list[tuple[str, str | None]] = []
    audits: list[dict[str, object]] = []

    async def fake_select_tasks(org_id: str, *, limit: int = 1000):
        assert org_id == ORG_ID
        return [
            {
                "id": TASK_A,
                "org_id": ORG_ID,
                "title": "Rotate access keys",
                "status": "open",
                "due_at": "2026-02-15T18:00:00Z",
                "severity": "high",
                "sla_state": "none",
            },
            {
                "id": TASK_B,
                "org_id": ORG_ID,
                "title": "Close exposed S3 bucket",
                "status": "in_progress",
                "due_at": "2026-02-14T09:00:00Z",
                "severity": "medium",
                "sla_state": "none",
            },
        ]

    async def fake_select_integration(access_token: str, org_id: str, integration_type: str):
        assert integration_type == "slack"
        return None

    async def fake_update_state(task_id: str, sla_state: str) -> None:
        state_updates.append((task_id, sla_state))

    async def fake_create_escalation(*, org_id: str, task_id: str, kind: str, window_start: str, channel: str):
        escalations.append(
            {
                "org_id": org_id,
                "task_id": task_id,
                "kind": kind,
                "window_start": window_start,
                "channel": channel,
            }
        )
        return {"id": f"esc-{len(escalations)}"}

    async def fake_enqueue(org_id: str, job_type: str, payload: dict[str, object], *, run_after: str | None = None):
        assert job_type == "sla"
        assert run_after is None
        jobs.append({"org_id": org_id, "payload": payload})
        return {"id": f"job-{len(jobs)}"}

    async def fake_mark(escalation_id: str, *, notification_job_id: str | None) -> None:
        marked.append((escalation_id, notification_job_id))

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        audits.append(payload)

    monkeypatch.setattr(sla_processor, "select_open_tasks_for_sla_service", fake_select_tasks)
    monkeypatch.setattr(sla_processor, "select_integration_secret", fake_select_integration)
    monkeypatch.setattr(sla_processor, "update_task_sla_state_service", fake_update_state)
    monkeypatch.setattr(sla_processor, "create_task_escalation_service", fake_create_escalation)
    monkeypatch.setattr(sla_processor, "enqueue_notification_job", fake_enqueue)
    monkeypatch.setattr(sla_processor, "mark_task_escalation_notified_service", fake_mark)
    monkeypatch.setattr(sla_processor, "rpc_record_audit_event", fake_audit)

    processor = sla_processor.SLAProcessor(access_token="service-role-token")
    queued = asyncio.run(
        processor._process_org(
            ORG_ID,
            {
                "due_soon_threshold_hours": 12,
                "overdue_remind_every_hours": 24,
            },
            datetime(2026, 2, 15, 10, 30, tzinfo=UTC),
        )
    )

    assert queued == 2
    assert ("22222222-2222-2222-2222-222222222222", "due_soon") in state_updates
    assert ("33333333-3333-3333-3333-333333333333", "overdue") in state_updates
    assert len(escalations) == 2
    assert escalations[0]["channel"] == "email"
    assert escalations[1]["channel"] == "email"
    assert str(escalations[0]["window_start"]).endswith("10:00:00Z")
    assert str(escalations[1]["window_start"]).endswith("00:00:00Z")
    assert len(jobs) == 2
    assert jobs[0]["payload"]["kind"] == "due_soon"
    assert jobs[1]["payload"]["kind"] == "overdue"
    assert len(marked) == 2
    assert len(audits) == 2


def test_sla_processor_overdue_window_idempotent(monkeypatch) -> None:
    seen_windows: set[tuple[str, str, str]] = set()
    jobs: list[dict[str, object]] = []

    async def fake_select_tasks(org_id: str, *, limit: int = 1000):
        return [
            {
                "id": TASK_B,
                "org_id": ORG_ID,
                "title": "Close exposed S3 bucket",
                "status": "in_progress",
                "due_at": "2026-02-14T09:00:00Z",
                "severity": "medium",
                "sla_state": "overdue",
            }
        ]

    async def fake_select_integration(access_token: str, org_id: str, integration_type: str):
        return None

    async def fake_update_state(task_id: str, sla_state: str) -> None:
        raise AssertionError("state should not change for already-overdue task")

    async def fake_create_escalation(*, org_id: str, task_id: str, kind: str, window_start: str, channel: str):
        key = (task_id, kind, window_start)
        if key in seen_windows:
            return None
        seen_windows.add(key)
        return {"id": "esc-1"}

    async def fake_enqueue(org_id: str, job_type: str, payload: dict[str, object], *, run_after: str | None = None):
        jobs.append(payload)
        return {"id": "job-1"}

    async def fake_mark(escalation_id: str, *, notification_job_id: str | None) -> None:
        return None

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        return None

    monkeypatch.setattr(sla_processor, "select_open_tasks_for_sla_service", fake_select_tasks)
    monkeypatch.setattr(sla_processor, "select_integration_secret", fake_select_integration)
    monkeypatch.setattr(sla_processor, "update_task_sla_state_service", fake_update_state)
    monkeypatch.setattr(sla_processor, "create_task_escalation_service", fake_create_escalation)
    monkeypatch.setattr(sla_processor, "enqueue_notification_job", fake_enqueue)
    monkeypatch.setattr(sla_processor, "mark_task_escalation_notified_service", fake_mark)
    monkeypatch.setattr(sla_processor, "rpc_record_audit_event", fake_audit)

    processor = sla_processor.SLAProcessor(access_token="service-role-token")
    now = datetime(2026, 2, 15, 10, 30, tzinfo=UTC)

    first = asyncio.run(
        processor._process_org(
            ORG_ID,
            {"due_soon_threshold_hours": 12, "overdue_remind_every_hours": 24},
            now,
        )
    )
    second = asyncio.run(
        processor._process_org(
            ORG_ID,
            {"due_soon_threshold_hours": 12, "overdue_remind_every_hours": 24},
            now,
        )
    )

    assert first == 1
    assert second == 0
    assert len(jobs) == 1
