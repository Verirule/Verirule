import asyncio

from app.worker import run_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "33333333-3333-3333-3333-333333333333"
FINDING_ID = "44444444-4444-4444-4444-444444444444"
ALERT_ID = "55555555-5555-5555-5555-555555555555"


def test_process_run_creates_explanation_when_content_changes(monkeypatch) -> None:
    run_state_updates: list[dict[str, str | None]] = []
    inserted_explanations: list[dict[str, object]] = []

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, str]]:
        assert access_token == "worker-token"
        assert limit == 5
        return [{"id": RUN_ID, "org_id": ORG_ID, "source_id": SOURCE_ID, "status": "queued"}]

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        assert access_token == "worker-token"
        run_state_updates.append(payload)

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object] | None:
        assert access_token == "worker-token"
        assert source_id == SOURCE_ID
        return {
            "id": SOURCE_ID,
            "org_id": ORG_ID,
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
            "etag": '"old-etag"',
            "last_modified": "Wed, 10 Feb 2026 00:00:00 GMT",
        }

    async def fake_fetch(
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
        *,
        timeout_seconds: float,
        max_bytes: int,
    ) -> dict[str, object]:
        assert url == "https://example.com/policy"
        assert etag == '"old-etag"'
        assert last_modified == "Wed, 10 Feb 2026 00:00:00 GMT"
        assert timeout_seconds == 10.0
        assert max_bytes == 1_000_000
        return {
            "status": 200,
            "bytes": b"<html><body>new text</body></html>",
            "content_type": "text/html",
            "etag": '"new-etag"',
            "last_modified": "Thu, 11 Feb 2026 00:00:00 GMT",
            "fetched_url": "https://example.com/policy",
        }

    def fake_normalize(content_type: str | None, content: bytes) -> dict[str, str]:
        assert content_type == "text/html"
        assert content
        return {
            "normalized_text": "new text preview",
            "text_preview": "new text preview",
            "text_fingerprint": "new-fingerprint",
        }

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
        assert payload["p_text_fingerprint"] == "new-fingerprint"
        return "snapshot-id"

    async def fake_upsert_finding(access_token: str, payload: dict[str, object]) -> str:
        assert access_token == "worker-token"
        assert payload["p_raw_hash"] == "new-fingerprint"
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

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "fetch_url", fake_fetch)
    monkeypatch.setattr(run_processor, "normalize", fake_normalize)
    monkeypatch.setattr(run_processor, "build_explanation", fake_build_explanation)
    monkeypatch.setattr(run_processor, "rpc_set_source_fetch_metadata", fake_set_source_metadata)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot_v2", fake_insert_snapshot)
    monkeypatch.setattr(run_processor, "rpc_upsert_finding", fake_upsert_finding)
    monkeypatch.setattr(run_processor, "rpc_insert_finding_explanation", fake_insert_explanation)
    monkeypatch.setattr(run_processor, "rpc_upsert_alert_for_finding", fake_upsert_alert)
    monkeypatch.setattr(run_processor, "rpc_append_audit", fake_append_audit)

    processor = run_processor.MonitorRunProcessor(access_token="worker-token")
    processed_count = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed_count == 1
    assert run_state_updates[0]["p_status"] == "running"
    assert run_state_updates[-1]["p_status"] == "succeeded"
    assert len(inserted_explanations) == 1
    assert inserted_explanations[0]["p_finding_id"] == FINDING_ID


def test_process_run_handles_304_without_finding(monkeypatch) -> None:
    run_state_updates: list[dict[str, str | None]] = []
    insert_snapshot_calls = 0
    upsert_finding_calls = 0

    async def fake_select_queued(access_token: str, limit: int) -> list[dict[str, str]]:
        return [{"id": RUN_ID, "org_id": ORG_ID, "source_id": SOURCE_ID, "status": "queued"}]

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        run_state_updates.append(payload)

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object]:
        return {
            "id": SOURCE_ID,
            "org_id": ORG_ID,
            "url": "https://example.com/policy",
            "is_enabled": True,
            "etag": '"old-etag"',
            "last_modified": "Wed, 10 Feb 2026 00:00:00 GMT",
        }

    async def fake_select_latest_snapshot(access_token: str, source_id: str) -> dict[str, str]:
        return {"etag": '"old-etag"', "last_modified": "Wed, 10 Feb 2026 00:00:00 GMT"}

    async def fake_fetch(
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
        *,
        timeout_seconds: float,
        max_bytes: int,
    ) -> dict[str, object]:
        return {
            "status": 304,
            "bytes": b"",
            "content_type": "text/html",
            "etag": '"old-etag"',
            "last_modified": "Wed, 10 Feb 2026 00:00:00 GMT",
            "fetched_url": "https://example.com/policy",
        }

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

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "fetch_url", fake_fetch)
    monkeypatch.setattr(run_processor, "rpc_set_source_fetch_metadata", fake_set_source_metadata)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot_v2", fake_insert_snapshot)
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
        return [{"id": RUN_ID, "org_id": ORG_ID, "source_id": SOURCE_ID, "status": "queued"}]

    async def fake_set_state(access_token: str, payload: dict[str, str | None]) -> None:
        called_write_tokens.append(access_token)

    async def fake_select_source(access_token: str, source_id: str) -> dict[str, object]:
        called_read_tokens.append(access_token)
        return {
            "id": SOURCE_ID,
            "org_id": ORG_ID,
            "url": "https://example.com/policy",
            "is_enabled": True,
            "etag": None,
            "last_modified": None,
        }

    async def fake_select_latest_snapshot(access_token: str, source_id: str) -> dict[str, str]:
        called_read_tokens.append(access_token)
        return {"text_fingerprint": "same-fingerprint", "text_preview": "same"}

    async def fake_fetch(
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
        *,
        timeout_seconds: float,
        max_bytes: int,
    ) -> dict[str, object]:
        return {
            "status": 200,
            "bytes": b"same",
            "content_type": "text/plain",
            "etag": None,
            "last_modified": None,
            "fetched_url": url,
        }

    def fake_normalize(content_type: str | None, content: bytes) -> dict[str, str]:
        return {
            "normalized_text": "same",
            "text_preview": "same",
            "text_fingerprint": "same-fingerprint",
        }

    async def fake_set_source_metadata(access_token: str, payload: dict[str, object]) -> None:
        called_write_tokens.append(access_token)

    async def fake_insert_snapshot(access_token: str, payload: dict[str, object]) -> str:
        called_write_tokens.append(access_token)
        return "snapshot-id"

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "fetch_url", fake_fetch)
    monkeypatch.setattr(run_processor, "normalize", fake_normalize)
    monkeypatch.setattr(run_processor, "rpc_set_source_fetch_metadata", fake_set_source_metadata)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot_v2", fake_insert_snapshot)

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
    assert scheduled_payloads == [
        {"p_source_id": "77777777-7777-7777-7777-777777777777"}
    ]
