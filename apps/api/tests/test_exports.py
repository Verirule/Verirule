import asyncio

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import exports as exports_endpoint
from app.billing import guard as billing_guard
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app
from app.worker import export_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
EXPORT_ID = "22222222-2222-2222-2222-222222222222"


async def _fake_paid_plan(access_token: str, org_id: str) -> dict[str, str]:
    assert access_token == "token-123"
    assert org_id == ORG_ID
    return {"id": org_id, "plan": "pro"}


@pytest.fixture(autouse=True)
def _default_paid_plan(monkeypatch) -> None:
    monkeypatch.setattr(billing_guard, "select_org_billing", _fake_paid_plan)


def test_create_export_requires_auth() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/exports", json={"org_id": ORG_ID, "format": "pdf"})
    assert response.status_code == 401


def test_list_exports_works(monkeypatch) -> None:
    async def fake_select_exports(access_token: str, org_id: str) -> list[dict[str, object]]:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return [
            {
                "id": EXPORT_ID,
                "org_id": ORG_ID,
                "requested_by_user_id": None,
                "format": "pdf",
                "scope": {"from": "2026-02-01T00:00:00Z"},
                "status": "queued",
                "file_path": None,
                "file_sha256": None,
                "error_text": None,
                "created_at": "2026-02-11T00:00:00Z",
                "completed_at": None,
            }
        ]

    monkeypatch.setattr(exports_endpoint, "select_audit_exports", fake_select_exports)
    monkeypatch.setattr(
        exports_endpoint,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "SUPABASE_SERVICE_ROLE_KEY": "service-role-123",
                "EXPORTS_BUCKET_NAME": "exports",
                "EXPORT_SIGNED_URL_SECONDS": 300,
            },
        )(),
    )
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get("/api/v1/exports", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "exports": [
            {
                "id": EXPORT_ID,
                "org_id": ORG_ID,
                "requested_by_user_id": None,
                "format": "pdf",
                "scope": {"from": "2026-02-01T00:00:00Z"},
                "status": "queued",
                "file_path": None,
                "file_sha256": None,
                "error_text": None,
                "created_at": "2026-02-11T00:00:00Z",
                "completed_at": None,
            }
        ]
    }


def test_download_url_requires_succeeded(monkeypatch) -> None:
    async def fake_select_export_by_id(
        access_token: str, export_id: str
    ) -> dict[str, object] | None:
        assert access_token == "token-123"
        assert export_id == EXPORT_ID
        return {
            "id": EXPORT_ID,
            "org_id": ORG_ID,
            "requested_by_user_id": None,
            "format": "csv",
            "scope": {},
            "status": "running",
            "file_path": None,
            "file_sha256": None,
            "error_text": None,
            "created_at": "2026-02-11T00:00:00Z",
            "completed_at": None,
        }

    monkeypatch.setattr(exports_endpoint, "select_audit_export_by_id", fake_select_export_by_id)
    monkeypatch.setattr(
        exports_endpoint,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "SUPABASE_SERVICE_ROLE_KEY": "service-role-123",
                "EXPORTS_BUCKET_NAME": "exports",
                "EXPORT_SIGNED_URL_SECONDS": 300,
            },
        )(),
    )
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/exports/{EXPORT_ID}/download-url")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {"detail": "Export is not ready for download."}


def test_create_export_returns_402_on_free_plan(monkeypatch) -> None:
    async def fake_free_plan(access_token: str, org_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return {"id": org_id, "plan": "free"}

    monkeypatch.setattr(billing_guard, "select_org_billing", fake_free_plan)
    monkeypatch.setattr(
        exports_endpoint,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "SUPABASE_SERVICE_ROLE_KEY": "service-role-123",
                "EXPORTS_BUCKET_NAME": "exports",
                "EXPORT_SIGNED_URL_SECONDS": 300,
            },
        )(),
    )
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post("/api/v1/exports", json={"org_id": ORG_ID, "format": "pdf"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 402
    assert response.json() == {"detail": "Upgrade required"}


def test_export_processor_uploads_and_updates_status(monkeypatch) -> None:
    started_attempts: list[tuple[str, int]] = []
    status_updates: list[dict[str, object]] = []
    uploaded: list[tuple[str, str, bytes, str]] = []

    async def fake_select_queued(limit: int = 3) -> list[dict[str, object]]:
        assert limit == 3
        return [
            {
                "id": EXPORT_ID,
                "org_id": ORG_ID,
                "requested_by_user_id": "user-1",
                "format": "pdf",
                "scope": {"from": "2026-02-01T00:00:00Z", "to": "2026-02-10T00:00:00Z"},
                "status": "queued",
                "created_at": "2026-02-11T00:00:00Z",
                "attempts": 0,
            }
        ]

    async def fake_select_packet(
        access_token: str, org_id: str, from_ts: str | None, to_ts: str | None
    ) -> dict[str, object]:
        assert access_token == "service-role-123"
        assert org_id == ORG_ID
        assert from_ts == "2026-02-01T00:00:00Z"
        assert to_ts == "2026-02-10T00:00:00Z"
        return {
            "org_id": ORG_ID,
            "from": from_ts,
            "to": to_ts,
            "findings": [],
            "alerts": [],
            "tasks": [],
            "task_evidence": [],
            "task_comments": [],
            "runs": [],
            "snapshots": [],
            "audit_timeline": [],
            "finding_explanations": [],
            "row_count": 0,
        }

    async def fake_update_status(
        export_id: str,
        status_value: str,
        file_path: str | None,
        file_sha256: str | None,
        error_text: str | None,
        completed_at: str | None,
    ) -> None:
        status_updates.append(
            {
                "id": export_id,
                "status": status_value,
                "file_path": file_path,
                "file_sha256": file_sha256,
                "error_text": error_text,
                "completed_at": completed_at,
            }
        )

    async def fake_mark_started(export_id: str, attempts: int) -> None:
        started_attempts.append((export_id, attempts))

    def fake_build_export_bytes(export_format: str, packet: dict[str, object]) -> tuple[bytes, str]:
        assert export_format == "pdf"
        assert packet.get("export_id") == EXPORT_ID
        return b"%PDF-1.4", "sha-123"

    async def fake_upload_bytes(bucket: str, path: str, data: bytes, content_type: str) -> None:
        uploaded.append((bucket, path, data, content_type))

    monkeypatch.setattr(export_processor, "select_queued_audit_exports_service", fake_select_queued)
    monkeypatch.setattr(export_processor, "select_audit_packet_data", fake_select_packet)
    monkeypatch.setattr(export_processor, "mark_audit_export_attempt_started", fake_mark_started)
    monkeypatch.setattr(export_processor, "update_audit_export_status", fake_update_status)
    monkeypatch.setattr(export_processor, "build_export_bytes", fake_build_export_bytes)
    monkeypatch.setattr(export_processor, "upload_bytes", fake_upload_bytes)

    processor = export_processor.ExportProcessor(
        access_token="service-role-123",
        bucket_name="exports",
    )
    processed_count = asyncio.run(processor.process_queued_exports_once(limit=3))

    assert processed_count == 1
    assert uploaded == [
        (
            "exports",
            f"org/{ORG_ID}/exports/{EXPORT_ID}.pdf",
            b"%PDF-1.4",
            "application/pdf",
        )
    ]
    assert started_attempts == [(EXPORT_ID, 1)]
    assert status_updates[-1]["status"] == "succeeded"
    assert status_updates[-1]["file_sha256"] == "sha-123"
