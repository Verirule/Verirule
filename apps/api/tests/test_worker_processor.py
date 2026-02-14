import asyncio
import hashlib
from datetime import UTC, datetime

from app.worker import run_processor
from app.worker.adapters.base import AdapterResult

ORG_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "33333333-3333-3333-3333-333333333333"
FINDING_ID = "44444444-4444-4444-4444-444444444444"
ALERT_ID = "55555555-5555-5555-5555-555555555555"


def test_process_run_creates_explanation_when_content_changes(monkeypatch) -> None:
    run_state_updates: list[dict[str, str | None]] = []
    inserted_explanations: list[dict[str, object]] = []
    immediate_calls: list[dict[str, str]] = []

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, str]]:
        assert access_token == "worker-token"
        assert limit == 5
        return [
            {"id": RUN_ID, "org_id": ORG_ID, "source_id": SOURCE_ID, "status": "queued", "attempts": 0}
        ]

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        assert access_token == "worker-token"
        run_state_updates.append(payload)

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object] | None:
        assert access_token == "worker-token"
        assert source_id == SOURCE_ID
        return {
            "id": SOURCE_ID,
            "org_id": ORG_ID,
            "kind": "html",
            "config": {},
            "url": "https://example.com/policy",
            "is_enabled": True,
            "etag": '"old-etag"',
            "last_modified": "Wed, 10 Feb 2026 00:00:00 GMT",
        }

    async def fake_select_latest_snapshot(access_token: str, source_id: str) -> dict[str, str] | None:
        assert access_token == "worker-token"
        assert source_id == SOURCE_ID
        return {
            "content_hash": "old-fingerprint",
            "text_fingerprint": "old-fingerprint",
            "text_preview": "old text preview",
            "canonical_text": "old text preview",
            "etag": '"old-etag"',
            "last_modified": "Wed, 10 Feb 2026 00:00:00 GMT",
        }

    class FakeAdapter:
        async def fetch(self, source, prev_snapshot):
            assert source.url == "https://example.com/policy"
            assert prev_snapshot is not None
            return AdapterResult(
                canonical_title="Policy",
                canonical_text="new text preview",
                content_type="text/html",
                etag='"new-etag"',
                last_modified="Thu, 11 Feb 2026 00:00:00 GMT",
                http_status=200,
                fetched_url=source.url,
                content_len=123,
            )

    def fake_get_adapter(kind: str):
        assert kind == "html"
        return FakeAdapter()

    def fake_build_explanation(prev_text: str, new_text: str) -> dict[str, object]:
        assert prev_text == "old text preview"
        assert new_text == "new text preview"
        return {
            "summary": "The source updated one section with a policy change.",
            "diff_preview": "@@ -1 +1 @@",
            "citations": [{"quote": "new text", "context": "@@ -1 +1 @@"}],
        }

    async def fake_set_source_metadata(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "worker-token"
        assert payload["p_source_id"] == SOURCE_ID
        assert payload["p_etag"] == '"new-etag"'

    async def fake_insert_snapshot(access_token: str, payload: dict[str, object]) -> str:
        assert access_token == "worker-token"
        assert payload["p_run_id"] == RUN_ID
        assert payload["p_http_status"] == 200
        assert payload["p_canonical_text"] == "new text preview"
        assert payload["p_canonical_title"] == "Policy"
        return "snapshot-id"

    async def fake_upsert_finding(access_token: str, payload: dict[str, object]) -> str:
        assert access_token == "worker-token"
        assert payload["p_raw_hash"]
        return FINDING_ID

    async def fake_insert_explanation(access_token: str, payload: dict[str, object]) -> str:
        assert access_token == "worker-token"
        inserted_explanations.append(payload)
        return "explanation-id"

    async def fake_upsert_alert(access_token: str, payload: dict[str, str]) -> dict[str, object]:
        assert access_token == "worker-token"
        assert payload == {"p_org_id": ORG_ID, "p_finding_id": FINDING_ID}
        return {"id": ALERT_ID, "created": True}

    async def fake_append_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "worker-token"
        assert payload["p_org_id"] == ORG_ID

    async def fake_mark_started(run_id: str, attempts: int) -> None:
        assert run_id == RUN_ID
        assert attempts == 1

    async def fake_clear_retry_state(run_id: str) -> None:
        assert run_id == RUN_ID

    async def fake_enqueue_immediate(self, *, org_id: str, alert_id: str, severity: str) -> None:
        immediate_calls.append({"org_id": org_id, "alert_id": alert_id, "severity": severity})

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "mark_monitor_run_attempt_started", fake_mark_started)
    monkeypatch.setattr(run_processor, "clear_monitor_run_error_state", fake_clear_retry_state)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "get_adapter", fake_get_adapter)
    monkeypatch.setattr(run_processor, "build_explanation", fake_build_explanation)
    monkeypatch.setattr(run_processor, "rpc_set_source_fetch_metadata", fake_set_source_metadata)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot_v3", fake_insert_snapshot)
    monkeypatch.setattr(run_processor, "rpc_upsert_finding", fake_upsert_finding)
    monkeypatch.setattr(run_processor, "rpc_insert_finding_explanation", fake_insert_explanation)
    monkeypatch.setattr(run_processor, "rpc_upsert_alert_for_finding", fake_upsert_alert)
    monkeypatch.setattr(run_processor, "rpc_append_audit", fake_append_audit)
    monkeypatch.setattr(
        run_processor.MonitorRunProcessor,
        "_enqueue_immediate_alert_if_needed",
        fake_enqueue_immediate,
    )

    processor = run_processor.MonitorRunProcessor(access_token="worker-token")
    processed_count = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed_count == 1
    assert run_state_updates[0]["p_status"] == "running"
    assert run_state_updates[-1]["p_status"] == "succeeded"
    assert len(inserted_explanations) == 1
    assert inserted_explanations[0]["p_finding_id"] == FINDING_ID
    assert immediate_calls == [{"org_id": ORG_ID, "alert_id": ALERT_ID, "severity": "medium"}]


def test_process_run_handles_304_without_finding(monkeypatch) -> None:
    run_state_updates: list[dict[str, str | None]] = []
    insert_snapshot_calls = 0
    upsert_finding_calls = 0

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, str]]:
        return [
            {"id": RUN_ID, "org_id": ORG_ID, "source_id": SOURCE_ID, "status": "queued", "attempts": 0}
        ]

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        run_state_updates.append(payload)

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object]:
        return {
            "id": SOURCE_ID,
            "org_id": ORG_ID,
            "kind": "html",
            "config": {},
            "url": "https://example.com/policy",
            "is_enabled": True,
            "etag": '"old-etag"',
            "last_modified": "Wed, 10 Feb 2026 00:00:00 GMT",
        }

    async def fake_select_latest_snapshot(access_token: str, source_id: str) -> dict[str, str]:
        return {"etag": '"old-etag"', "last_modified": "Wed, 10 Feb 2026 00:00:00 GMT"}

    class FakeAdapter:
        async def fetch(self, source, prev_snapshot):
            return AdapterResult(
                canonical_text="",
                content_type="text/html",
                etag='"old-etag"',
                last_modified="Wed, 10 Feb 2026 00:00:00 GMT",
                http_status=304,
                fetched_url=source.url,
                content_len=0,
            )

    def fake_get_adapter(kind: str):
        return FakeAdapter()

    async def fake_set_source_metadata(access_token: str, payload: dict[str, object]) -> None:
        return None

    async def fake_insert_snapshot(access_token: str, payload: dict[str, object]) -> str:
        nonlocal insert_snapshot_calls
        insert_snapshot_calls += 1
        return "snapshot-id"

    async def fake_upsert_finding(access_token: str, payload: dict[str, object]) -> str:
        nonlocal upsert_finding_calls
        upsert_finding_calls += 1
        return FINDING_ID

    async def fake_mark_started(run_id: str, attempts: int) -> None:
        assert run_id == RUN_ID
        assert attempts == 1

    async def fake_clear_retry_state(run_id: str) -> None:
        assert run_id == RUN_ID

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "mark_monitor_run_attempt_started", fake_mark_started)
    monkeypatch.setattr(run_processor, "clear_monitor_run_error_state", fake_clear_retry_state)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "get_adapter", fake_get_adapter)
    monkeypatch.setattr(run_processor, "rpc_set_source_fetch_metadata", fake_set_source_metadata)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot_v3", fake_insert_snapshot)
    monkeypatch.setattr(run_processor, "rpc_upsert_finding", fake_upsert_finding)

    processor = run_processor.MonitorRunProcessor(access_token="worker-token")
    processed_count = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed_count == 1
    assert run_state_updates[0]["p_status"] == "running"
    assert run_state_updates[-1]["p_status"] == "succeeded"
    assert insert_snapshot_calls == 0
    assert upsert_finding_calls == 0


def test_process_run_uses_service_role_for_writes(monkeypatch) -> None:
    read_token = "worker-read-token"
    write_token = "service-role-token"
    called_read_tokens: list[str] = []
    called_write_tokens: list[str] = []

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, str]]:
        called_read_tokens.append(access_token)
        return [
            {"id": RUN_ID, "org_id": ORG_ID, "source_id": SOURCE_ID, "status": "queued", "attempts": 0}
        ]

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        called_write_tokens.append(access_token)

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object]:
        called_read_tokens.append(access_token)
        return {
            "id": SOURCE_ID,
            "org_id": ORG_ID,
            "kind": "html",
            "config": {},
            "url": "https://example.com/policy",
            "is_enabled": True,
            "etag": None,
            "last_modified": None,
        }

    async def fake_select_latest_snapshot(access_token: str, source_id: str) -> dict[str, str]:
        called_read_tokens.append(access_token)
        return {
            "text_fingerprint": hashlib.sha256(b"same").hexdigest(),
            "canonical_text": "same",
        }

    class FakeAdapter:
        async def fetch(self, source, prev_snapshot):
            return AdapterResult(
                canonical_text="same",
                content_type="text/plain",
                etag=None,
                last_modified=None,
                http_status=200,
                fetched_url=source.url,
                content_len=4,
            )

    def fake_get_adapter(kind: str):
        return FakeAdapter()

    async def fake_set_source_metadata(access_token: str, payload: dict[str, object]) -> None:
        called_write_tokens.append(access_token)

    async def fake_insert_snapshot(access_token: str, payload: dict[str, object]) -> str:
        called_write_tokens.append(access_token)
        return "snapshot-id"

    async def fake_mark_started(run_id: str, attempts: int) -> None:
        assert run_id == RUN_ID
        assert attempts == 1

    async def fake_clear_retry_state(run_id: str) -> None:
        assert run_id == RUN_ID

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "mark_monitor_run_attempt_started", fake_mark_started)
    monkeypatch.setattr(run_processor, "clear_monitor_run_error_state", fake_clear_retry_state)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "get_adapter", fake_get_adapter)
    monkeypatch.setattr(run_processor, "rpc_set_source_fetch_metadata", fake_set_source_metadata)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot_v3", fake_insert_snapshot)

    processor = run_processor.MonitorRunProcessor(
        access_token=read_token,
        write_access_token=write_token,
    )
    processed_count = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed_count == 1
    assert called_read_tokens
    assert called_write_tokens
    assert all(token == read_token for token in called_read_tokens)
    assert all(token == write_token for token in called_write_tokens)


def test_process_run_rss_item_id_dedupes(monkeypatch) -> None:
    snapshot_insert_calls = 0

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, str]]:
        return [
            {"id": RUN_ID, "org_id": ORG_ID, "source_id": SOURCE_ID, "status": "queued", "attempts": 0}
        ]

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        return None

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object]:
        return {
            "id": SOURCE_ID,
            "org_id": ORG_ID,
            "kind": "rss",
            "config": {},
            "url": "https://example.com/feed.xml",
            "is_enabled": True,
            "etag": None,
            "last_modified": None,
        }

    async def fake_select_latest_snapshot(access_token: str, source_id: str) -> dict[str, object]:
        return {
            "item_id": "same-item",
            "text_fingerprint": "old-fingerprint",
            "canonical_text": "old",
        }

    class FakeAdapter:
        async def fetch(self, source, prev_snapshot):
            return AdapterResult(
                canonical_title="Post",
                canonical_text="",
                item_id="same-item",
                item_published_at=datetime(2026, 2, 12, tzinfo=UTC),
                content_type="application/rss+xml",
                http_status=200,
                fetched_url=source.url,
                content_len=100,
            )

    def fake_get_adapter(kind: str):
        assert kind == "rss"
        return FakeAdapter()

    async def fake_set_source_metadata(access_token: str, payload: dict[str, object]) -> None:
        return None

    async def fake_insert_snapshot(access_token: str, payload: dict[str, object]) -> str:
        nonlocal snapshot_insert_calls
        snapshot_insert_calls += 1
        return "snapshot-id"

    async def fake_mark_started(run_id: str, attempts: int) -> None:
        assert attempts == 1

    async def fake_clear_retry_state(run_id: str) -> None:
        return None

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "mark_monitor_run_attempt_started", fake_mark_started)
    monkeypatch.setattr(run_processor, "clear_monitor_run_error_state", fake_clear_retry_state)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "get_adapter", fake_get_adapter)
    monkeypatch.setattr(run_processor, "rpc_set_source_fetch_metadata", fake_set_source_metadata)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot_v3", fake_insert_snapshot)

    processor = run_processor.MonitorRunProcessor(access_token="worker-token")
    processed_count = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed_count == 1
    assert snapshot_insert_calls == 0


def test_process_run_rss_stores_item_id(monkeypatch) -> None:
    inserted_snapshot_payloads: list[dict[str, object]] = []

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, str]]:
        return [
            {"id": RUN_ID, "org_id": ORG_ID, "source_id": SOURCE_ID, "status": "queued", "attempts": 0}
        ]

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        return None

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object]:
        return {
            "id": SOURCE_ID,
            "org_id": ORG_ID,
            "kind": "rss",
            "config": {},
            "url": "https://example.com/feed.xml",
            "is_enabled": True,
            "etag": None,
            "last_modified": None,
        }

    async def fake_select_latest_snapshot(access_token: str, source_id: str) -> dict[str, object] | None:
        return None

    class FakeAdapter:
        async def fetch(self, source, prev_snapshot):
            return AdapterResult(
                canonical_title="Post",
                canonical_text="Body text",
                item_id="entry-123",
                item_published_at=datetime(2026, 2, 12, tzinfo=UTC),
                content_type="application/rss+xml",
                http_status=200,
                fetched_url=source.url,
                content_len=256,
            )

    def fake_get_adapter(kind: str):
        return FakeAdapter()

    async def fake_set_source_metadata(access_token: str, payload: dict[str, object]) -> None:
        return None

    async def fake_insert_snapshot(access_token: str, payload: dict[str, object]) -> str:
        inserted_snapshot_payloads.append(payload)
        return "snapshot-id"

    async def fake_upsert_finding(access_token: str, payload: dict[str, object]) -> str:
        return FINDING_ID

    async def fake_insert_explanation(access_token: str, payload: dict[str, object]) -> str:
        return "exp-id"

    async def fake_alert(access_token: str, payload: dict[str, str]) -> dict[str, object]:
        return {"id": ALERT_ID}

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        return None

    async def fake_mark_started(run_id: str, attempts: int) -> None:
        assert attempts == 1

    async def fake_clear_retry_state(run_id: str) -> None:
        return None

    async def fake_enqueue_immediate(self, *, org_id: str, alert_id: str, severity: str) -> None:
        return None

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "mark_monitor_run_attempt_started", fake_mark_started)
    monkeypatch.setattr(run_processor, "clear_monitor_run_error_state", fake_clear_retry_state)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "get_adapter", fake_get_adapter)
    monkeypatch.setattr(run_processor, "rpc_set_source_fetch_metadata", fake_set_source_metadata)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot_v3", fake_insert_snapshot)
    monkeypatch.setattr(run_processor, "rpc_upsert_finding", fake_upsert_finding)
    monkeypatch.setattr(run_processor, "rpc_insert_finding_explanation", fake_insert_explanation)
    monkeypatch.setattr(run_processor, "rpc_upsert_alert_for_finding", fake_alert)
    monkeypatch.setattr(run_processor, "rpc_append_audit", fake_audit)
    monkeypatch.setattr(
        run_processor.MonitorRunProcessor,
        "_enqueue_immediate_alert_if_needed",
        fake_enqueue_immediate,
    )

    processor = run_processor.MonitorRunProcessor(access_token="worker-token")
    processed_count = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed_count == 1
    assert len(inserted_snapshot_payloads) == 1
    assert inserted_snapshot_payloads[0]["p_item_id"] == "entry-123"
    assert inserted_snapshot_payloads[0]["p_canonical_title"] == "Post"


def test_queue_due_sources_once_queues_single_run_with_safety_window(monkeypatch) -> None:
    due_sources = [
        {"id": SOURCE_ID, "org_id": ORG_ID, "next_run_at": "2026-02-11T00:00:00Z"},
        {"id": "77777777-7777-7777-7777-777777777777", "org_id": ORG_ID, "next_run_at": "2026-02-11T00:00:00Z"},
    ]
    queued_payloads: list[dict[str, str]] = []
    scheduled_payloads: list[dict[str, str]] = []

    async def fake_select_due(access_token: str, org_id: str | None = None) -> list[dict[str, str]]:
        assert access_token == "worker-token"
        assert org_id is None
        return due_sources

    async def fake_select_recent_active(
        access_token: str, source_id: str, created_after_iso: str
    ) -> list[dict[str, str]]:
        assert access_token == "worker-token"
        assert created_after_iso.endswith("Z")
        if source_id == SOURCE_ID:
            return [{"id": RUN_ID, "source_id": SOURCE_ID, "status": "queued"}]
        return []

    async def fake_create_run(access_token: str, payload: dict[str, str]) -> str:
        assert access_token == "worker-token"
        queued_payloads.append(payload)
        return "run-created"

    async def fake_schedule_next(access_token: str, payload: dict[str, str]) -> None:
        assert access_token == "worker-token"
        scheduled_payloads.append(payload)

    monkeypatch.setattr(run_processor, "select_due_sources", fake_select_due)
    monkeypatch.setattr(
        run_processor,
        "select_recent_active_monitor_runs_for_source",
        fake_select_recent_active,
    )
    monkeypatch.setattr(run_processor, "rpc_create_monitor_run", fake_create_run)
    monkeypatch.setattr(run_processor, "rpc_schedule_next_run", fake_schedule_next)

    processor = run_processor.MonitorRunProcessor(access_token="worker-token")
    queued_count = asyncio.run(processor.queue_due_sources_once(limit=10))

    assert queued_count == 1
    assert queued_payloads == [
        {
            "p_org_id": ORG_ID,
            "p_source_id": "77777777-7777-7777-7777-777777777777",
        }
    ]
    assert scheduled_payloads == [{"p_source_id": "77777777-7777-7777-7777-777777777777"}]


def test_enqueue_immediate_alert_if_needed_enqueues_when_rules_match(monkeypatch) -> None:
    ensured: list[tuple[str, str]] = []
    enqueued: list[dict[str, object]] = []

    async def fake_ensure(access_token: str, org_id: str) -> None:
        ensured.append((access_token, org_id))

    async def fake_get_rules(access_token: str, org_id: str) -> dict[str, object]:
        assert access_token == "write-token"
        assert org_id == ORG_ID
        return {"enabled": True, "mode": "both", "min_severity": "high"}

    async def fake_enqueue(org_id: str, job_type: str, payload: dict[str, object], *, run_after=None):
        enqueued.append({"org_id": org_id, "job_type": job_type, "payload": payload, "run_after": run_after})
        return {"id": "job-1"}

    monkeypatch.setattr(run_processor, "ensure_org_notification_rules", fake_ensure)
    monkeypatch.setattr(run_processor, "get_org_notification_rules", fake_get_rules)
    monkeypatch.setattr(run_processor, "enqueue_notification_job", fake_enqueue)

    processor = run_processor.MonitorRunProcessor(
        access_token="read-token",
        write_access_token="write-token",
    )
    asyncio.run(
        processor._enqueue_immediate_alert_if_needed(
            org_id=ORG_ID,
            alert_id=ALERT_ID,
            severity="high",
        )
    )

    assert ensured == [("write-token", ORG_ID)]
    assert len(enqueued) == 1
    assert enqueued[0]["org_id"] == ORG_ID
    assert enqueued[0]["job_type"] == "immediate_alert"
    assert enqueued[0]["payload"] == {
        "org_id": ORG_ID,
        "alert_id": ALERT_ID,
        "entity_type": "alert",
        "entity_id": ALERT_ID,
    }
