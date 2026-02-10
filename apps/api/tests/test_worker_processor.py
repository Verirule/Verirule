import asyncio
import hashlib
import ipaddress

import pytest

from app.worker import run_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "33333333-3333-3333-3333-333333333333"
FINDING_ID = "44444444-4444-4444-4444-444444444444"
ALERT_ID = "55555555-5555-5555-5555-555555555555"


def test_validate_fetch_url_rejects_private_ip_ranges() -> None:
    with pytest.raises(run_processor.UnsafeUrlError):
        run_processor.validate_fetch_url("http://127.0.0.1/internal")

    with pytest.raises(run_processor.UnsafeUrlError):
        run_processor.validate_fetch_url("http://169.254.169.254/latest/meta-data")


def test_fetch_url_snapshot_hashes_content_with_mocked_httpx(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200
        headers = {"content-type": "text/plain", "content-length": "5"}
        url = "https://example.com/policy"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        async def aiter_bytes(self):
            yield b"he"
            yield b"llo"

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            assert kwargs["follow_redirects"] is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        def stream(self, method: str, url: str, headers: dict[str, str]) -> FakeResponse:
            assert method == "GET"
            assert url == "https://example.com/policy"
            assert "User-Agent" in headers
            return FakeResponse()

    monkeypatch.setattr(run_processor, "resolve_public_ips", lambda host: [ipaddress.ip_address("93.184.216.34")])
    monkeypatch.setattr(run_processor.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(run_processor.fetch_url_snapshot("https://example.com/policy"))

    assert result["content_hash"] == hashlib.sha256(b"hello").hexdigest()
    assert result["content_len"] == 5
    assert result["content_type"] == "text/plain"


def test_process_run_creates_finding_when_hash_changes(monkeypatch) -> None:
    run_state_updates: list[dict[str, str | None]] = []
    finding_payloads: list[dict[str, str]] = []
    alert_payloads: list[dict[str, str]] = []
    audit_payloads: list[dict[str, object]] = []

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
        }

    async def fake_select_latest_snapshot(access_token: str, source_id: str) -> dict[str, str] | None:
        assert access_token == "worker-token"
        assert source_id == SOURCE_ID
        return {"content_hash": "old-hash"}

    async def fake_insert_snapshot(access_token: str, payload: dict[str, object]) -> str:
        assert access_token == "worker-token"
        assert payload["p_run_id"] == RUN_ID
        assert payload["p_source_id"] == SOURCE_ID
        return "snapshot-id"

    async def fake_upsert_finding(access_token: str, payload: dict[str, str]) -> str:
        assert access_token == "worker-token"
        finding_payloads.append(payload)
        return FINDING_ID

    async def fake_upsert_alert(access_token: str, payload: dict[str, str]) -> dict[str, object]:
        assert access_token == "worker-token"
        alert_payloads.append(payload)
        return {"id": ALERT_ID, "created": True}

    async def fake_append_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "worker-token"
        audit_payloads.append(payload)

    async def fake_fetch(url: str, *, timeout_seconds: float, max_bytes: int) -> dict[str, object]:
        assert url == "https://example.com/policy"
        assert timeout_seconds == 10.0
        assert max_bytes == 1_000_000
        return {
            "fetched_url": "https://example.com/policy",
            "content_hash": "new-hash",
            "content_type": "text/html",
            "content_len": 123,
        }

    monkeypatch.setattr(run_processor, "select_queued_monitor_runs", fake_select_queued)
    monkeypatch.setattr(run_processor, "rpc_set_monitor_run_state", fake_set_state)
    monkeypatch.setattr(run_processor, "select_source_by_id", fake_select_source)
    monkeypatch.setattr(run_processor, "select_latest_snapshot", fake_select_latest_snapshot)
    monkeypatch.setattr(run_processor, "rpc_insert_snapshot", fake_insert_snapshot)
    monkeypatch.setattr(run_processor, "rpc_upsert_finding", fake_upsert_finding)
    monkeypatch.setattr(run_processor, "rpc_upsert_alert_for_finding", fake_upsert_alert)
    monkeypatch.setattr(run_processor, "rpc_append_audit", fake_append_audit)
    monkeypatch.setattr(run_processor, "fetch_url_snapshot", fake_fetch)

    processor = run_processor.MonitorRunProcessor(access_token="worker-token")
    processed_count = asyncio.run(processor.process_queued_runs_once(limit=5))

    assert processed_count == 1
    assert run_state_updates[0]["p_status"] == "running"
    assert run_state_updates[-1]["p_status"] == "succeeded"
    assert len(finding_payloads) == 1
    assert finding_payloads[0]["p_raw_hash"] == "new-hash"
    assert len(alert_payloads) == 1
    assert alert_payloads[0]["p_finding_id"] == FINDING_ID
    assert len(audit_payloads) == 1
