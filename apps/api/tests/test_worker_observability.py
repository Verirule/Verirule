import asyncio

from app import __main__ as app_main
from app.worker import export_processor, run_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "33333333-3333-3333-3333-333333333333"
EXPORT_ID = "44444444-4444-4444-4444-444444444444"


def test_run_retry_schedules_next_attempt(monkeypatch) -> None:
    retries: list[dict[str, object]] = []

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, object]]:
        return [
            {
                "id": RUN_ID,
                "org_id": ORG_ID,
                "source_id": SOURCE_ID,
                "status": "queued",
                "attempts": 0,
            }
        ]

    async def fake_mark_started(run_id: str, attempts: int) -> None:
        assert run_id == RUN_ID
        assert attempts == 1

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        assert payload["p_status"] == "running"

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object] | None:
        return None

    async def fake_mark_retry(
        run_id: str, attempts: int, next_attempt_at: str, last_error: str
    ) -> None:
        retries.append(
            {
                "run_id": run_id,
                "attempts": attempts,
                "next_attempt_at": next_attempt_at,
                "last_error": last_error,
            }
        )

    async def fake_dead_letter(run_id: str, attempts: int, last_error: str, failed_at: str) -> None:
        raise AssertionError("dead-letter should not be called for attempt 1")

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "mark_monitor_run_attempt_started", fake_mark_started)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "mark_monitor_run_for_retry", fake_mark_retry)
    monkeypatch.setattr(run_processor, "mark_monitor_run_dead_letter", fake_dead_letter)

    processor = run_processor.MonitorRunProcessor(access_token="service-role-123")
    processed = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed == 1
    assert len(retries) == 1
    assert retries[0]["run_id"] == RUN_ID
    assert retries[0]["attempts"] == 1
    assert str(retries[0]["next_attempt_at"]).endswith("Z")


def test_run_dead_letter_after_five_attempts(monkeypatch) -> None:
    dead_letters: list[dict[str, object]] = []

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, object]]:
        return [
            {
                "id": RUN_ID,
                "org_id": ORG_ID,
                "source_id": SOURCE_ID,
                "status": "queued",
                "attempts": 4,
            }
        ]

    async def fake_mark_started(run_id: str, attempts: int) -> None:
        assert attempts == 5

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        assert payload["p_status"] == "running"

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object] | None:
        return None

    async def fake_mark_retry(
        run_id: str, attempts: int, next_attempt_at: str, last_error: str
    ) -> None:
        raise AssertionError("retry should not be scheduled after 5th attempt")

    async def fake_dead_letter(run_id: str, attempts: int, last_error: str, failed_at: str) -> None:
        dead_letters.append(
            {
                "run_id": run_id,
                "attempts": attempts,
                "last_error": last_error,
                "failed_at": failed_at,
            }
        )

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "mark_monitor_run_attempt_started", fake_mark_started)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "mark_monitor_run_for_retry", fake_mark_retry)
    monkeypatch.setattr(run_processor, "mark_monitor_run_dead_letter", fake_dead_letter)

    processor = run_processor.MonitorRunProcessor(access_token="service-role-123")
    processed = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed == 1
    assert len(dead_letters) == 1
    assert dead_letters[0]["attempts"] == 5
    assert str(dead_letters[0]["failed_at"]).endswith("Z")


def test_export_dead_letter_after_five_attempts(monkeypatch) -> None:
    dead_letters: list[dict[str, object]] = []

    async def fake_select_queued(limit: int = 3) -> list[dict[str, object]]:
        return [
            {
                "id": EXPORT_ID,
                "org_id": ORG_ID,
                "format": "pdf",
                "scope": {},
                "status": "queued",
                "attempts": 4,
            }
        ]

    async def fake_mark_started(export_id: str, attempts: int) -> None:
        assert export_id == EXPORT_ID
        assert attempts == 5

    async def fake_select_packet(
        access_token: str, org_id: str, from_ts: str | None, to_ts: str | None
    ) -> dict[str, object]:
        raise ValueError("packet failed")

    async def fake_retry(
        export_id: str, attempts: int, next_attempt_at: str, last_error: str
    ) -> None:
        raise AssertionError("retry should not be scheduled after 5th attempt")

    async def fake_dead_letter(
        export_id: str, attempts: int, last_error: str, completed_at: str
    ) -> None:
        dead_letters.append(
            {
                "export_id": export_id,
                "attempts": attempts,
                "last_error": last_error,
                "completed_at": completed_at,
            }
        )

    monkeypatch.setattr(export_processor, "select_queued_audit_exports_service", fake_select_queued)
    monkeypatch.setattr(export_processor, "mark_audit_export_attempt_started", fake_mark_started)
    monkeypatch.setattr(export_processor, "select_audit_packet_data", fake_select_packet)
    monkeypatch.setattr(export_processor, "mark_audit_export_for_retry", fake_retry)
    monkeypatch.setattr(export_processor, "mark_audit_export_dead_letter", fake_dead_letter)

    processor = export_processor.ExportProcessor(
        access_token="service-role-123",
        bucket_name="exports",
    )
    processed = asyncio.run(processor.process_queued_exports_once(limit=3))

    assert processed == 1
    assert len(dead_letters) == 1
    assert dead_letters[0]["attempts"] == 5
    assert str(dead_letters[0]["completed_at"]).endswith("Z")


def test_export_retry_schedules_next_attempt(monkeypatch) -> None:
    retries: list[dict[str, object]] = []

    async def fake_select_queued(limit: int = 3) -> list[dict[str, object]]:
        return [
            {
                "id": EXPORT_ID,
                "org_id": ORG_ID,
                "format": "csv",
                "scope": {},
                "status": "queued",
                "attempts": 0,
            }
        ]

    async def fake_mark_started(export_id: str, attempts: int) -> None:
        assert export_id == EXPORT_ID
        assert attempts == 1

    async def fake_select_packet(
        access_token: str, org_id: str, from_ts: str | None, to_ts: str | None
    ) -> dict[str, object]:
        raise ValueError("packet failed")

    async def fake_retry(
        export_id: str, attempts: int, next_attempt_at: str, last_error: str
    ) -> None:
        retries.append(
            {
                "export_id": export_id,
                "attempts": attempts,
                "next_attempt_at": next_attempt_at,
                "last_error": last_error,
            }
        )

    async def fake_dead_letter(
        export_id: str, attempts: int, last_error: str, completed_at: str
    ) -> None:
        raise AssertionError("dead-letter should not be called for attempt 1")

    monkeypatch.setattr(export_processor, "select_queued_audit_exports_service", fake_select_queued)
    monkeypatch.setattr(export_processor, "mark_audit_export_attempt_started", fake_mark_started)
    monkeypatch.setattr(export_processor, "select_audit_packet_data", fake_select_packet)
    monkeypatch.setattr(export_processor, "mark_audit_export_for_retry", fake_retry)
    monkeypatch.setattr(export_processor, "mark_audit_export_dead_letter", fake_dead_letter)

    processor = export_processor.ExportProcessor(
        access_token="service-role-123",
        bucket_name="exports",
    )
    processed = asyncio.run(processor.process_queued_exports_once(limit=3))

    assert processed == 1
    assert len(retries) == 1
    assert retries[0]["attempts"] == 1
    assert str(retries[0]["next_attempt_at"]).endswith("Z")


def test_worker_heartbeat_upsert_called(monkeypatch) -> None:
    upserts: list[tuple[str, dict[str, object]]] = []

    class FakeMonitorProcessor:
        async def count_due_sources_once(self) -> int:
            return 4

        async def queue_due_sources_once(self, limit: int = 10) -> int:
            assert limit == 10
            return 2

        async def process_queued_runs_once(self, limit: int = 5) -> int:
            assert limit == 5
            return 1

    class FakeExportProcessor:
        async def process_queued_exports_once(self, limit: int = 3) -> int:
            assert limit == 3
            return 1

    class FakeAlertTaskProcessor:
        async def process_alerts_once(self, limit: int = 25) -> int:
            assert limit == 25
            return 2

    class FakeReadinessProcessor:
        async def process_if_due(self) -> int:
            return 3

    class FakeDigestProcessor:
        async def process_if_due(self) -> int:
            return 1

    class FakeNotificationSender:
        async def process_queued_jobs_once(self) -> int:
            return 2

    async def fake_upsert_system_status(status_id: str, payload: dict[str, object]) -> None:
        upserts.append((status_id, payload))

    monkeypatch.setattr(app_main, "upsert_system_status", fake_upsert_system_status)

    payload = asyncio.run(
        app_main.run_worker_tick(
            FakeMonitorProcessor(),  # type: ignore[arg-type]
            FakeExportProcessor(),  # type: ignore[arg-type]
            FakeAlertTaskProcessor(),  # type: ignore[arg-type]
            FakeReadinessProcessor(),  # type: ignore[arg-type]
            FakeDigestProcessor(),  # type: ignore[arg-type]
            FakeNotificationSender(),  # type: ignore[arg-type]
            run_batch_limit=5,
            heartbeat_enabled=True,
        )
    )

    assert payload["mode"] == "worker"
    assert payload["runs_processed"] == 1
    assert payload["exports_processed"] == 1
    assert payload["alert_tasks_processed"] == 2
    assert payload["readiness_computed"] == 3
    assert payload["digests_sent"] == 1
    assert payload["notification_emails_sent"] == 2
    assert payload["runs_queued"] == 2
    assert payload["due_sources"] == 4
    assert payload["errors"] == 0
    assert str(payload["tick_started_at"]).endswith("Z")
    assert str(payload["tick_finished_at"]).endswith("Z")
    assert len(upserts) == 1
    assert upserts[0][0] == "worker"
