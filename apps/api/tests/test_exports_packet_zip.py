import asyncio
import json
import zipfile
from io import BytesIO

from fastapi.testclient import TestClient

from app.api.v1.endpoints import exports as exports_endpoint
from app.billing import guard as billing_guard
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app
from app.worker import export_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
EXPORT_ID = "22222222-2222-2222-2222-222222222222"
TASK_ID = "33333333-3333-3333-3333-333333333333"
EVIDENCE_ID_1 = "44444444-4444-4444-4444-444444444444"
EVIDENCE_ID_2 = "55555555-5555-5555-5555-555555555555"


def _zip_names(data: bytes) -> list[str]:
    with zipfile.ZipFile(BytesIO(data), "r") as archive:
        return sorted(archive.namelist())


def _zip_json(data: bytes, path: str) -> dict[str, object]:
    with zipfile.ZipFile(BytesIO(data), "r") as archive:
        with archive.open(path) as handle:
            return json.loads(handle.read().decode("utf-8"))


def test_create_zip_export_queues(monkeypatch) -> None:
    async def fake_create_export(access_token: str, payload: dict[str, object]) -> str:
        assert access_token == "token-123"
        assert payload["p_org_id"] == ORG_ID
        assert payload["p_format"] == "zip"
        return EXPORT_ID

    monkeypatch.setattr(exports_endpoint, "rpc_create_audit_export", fake_create_export)
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

    async def fake_paid_plan(access_token: str, org_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return {"id": org_id, "plan": "pro"}

    monkeypatch.setattr(billing_guard, "select_org_billing", fake_paid_plan)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post("/api/v1/exports", json={"org_id": ORG_ID, "format": "zip"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": EXPORT_ID, "status": "queued"}


def test_zip_export_processor_writes_audit_packet(monkeypatch) -> None:
    uploaded: list[tuple[str, str, bytes, str]] = []

    async def fake_select_queued(limit: int = 3) -> list[dict[str, object]]:
        assert limit == 3
        return [
            {
                "id": EXPORT_ID,
                "org_id": ORG_ID,
                "format": "zip",
                "scope": {},
                "status": "queued",
                "attempts": 0,
            }
        ]

    async def fake_select_packet(
        access_token: str, org_id: str, from_ts: str | None, to_ts: str | None
    ) -> dict[str, object]:
        assert access_token == "service-role-123"
        assert org_id == ORG_ID
        assert from_ts is None
        assert to_ts is None
        return {
            "org_id": ORG_ID,
            "findings": [],
            "alerts": [],
            "tasks": [{"id": TASK_ID}],
            "task_evidence": [],
            "evidence_files": [
                {
                    "id": EVIDENCE_ID_1,
                    "task_id": TASK_ID,
                    "filename": "proof.txt",
                    "storage_bucket": "evidence",
                    "storage_path": f"orgs/{ORG_ID}/tasks/{TASK_ID}/proof.txt",
                    "created_at": "2026-02-10T00:00:00Z",
                }
            ],
            "task_comments": [],
            "runs": [],
            "snapshots": [],
            "audit_timeline": [],
            "readiness_summary": {
                "id": "66666666-6666-6666-6666-666666666666",
                "org_id": ORG_ID,
                "computed_at": "2026-02-13T00:00:00Z",
                "score": 78,
                "controls_total": 20,
                "controls_with_evidence": 12,
                "evidence_items_total": 40,
                "evidence_items_done": 24,
                "open_alerts_high": 2,
                "open_tasks": 5,
                "overdue_tasks": 1,
                "metadata": {},
            },
            "finding_explanations": [],
            "row_count": 1,
        }

    async def fake_update_status(
        export_id: str,
        status_value: str,
        file_path: str | None,
        file_sha256: str | None,
        error_text: str | None,
        completed_at: str | None,
    ) -> None:
        assert export_id == EXPORT_ID
        assert status_value in {"running", "succeeded"}
        if status_value == "succeeded":
            assert file_path == f"org/{ORG_ID}/exports/{EXPORT_ID}.zip"
            assert isinstance(file_sha256, str) and len(file_sha256) == 64
            assert error_text is None
            assert isinstance(completed_at, str)

    async def fake_mark_started(export_id: str, attempts: int) -> None:
        assert export_id == EXPORT_ID
        assert attempts == 1

    async def fake_download_bytes(bucket: str, path: str) -> bytes:
        assert bucket == "evidence"
        assert path == f"orgs/{ORG_ID}/tasks/{TASK_ID}/proof.txt"
        return b"proof-bytes"

    async def fake_upload_bytes(bucket: str, path: str, data: bytes, content_type: str) -> None:
        uploaded.append((bucket, path, data, content_type))

    monkeypatch.setattr(export_processor, "select_queued_audit_exports_service", fake_select_queued)
    monkeypatch.setattr(export_processor, "select_audit_packet_data", fake_select_packet)
    monkeypatch.setattr(export_processor, "mark_audit_export_attempt_started", fake_mark_started)
    monkeypatch.setattr(export_processor, "update_audit_export_status", fake_update_status)
    monkeypatch.setattr(export_processor, "download_bytes", fake_download_bytes)
    monkeypatch.setattr(export_processor, "upload_bytes", fake_upload_bytes)
    def fake_build_pdf(packet: dict[str, object]) -> bytes:
        readiness = packet.get("readiness_summary")
        assert isinstance(readiness, dict)
        assert readiness.get("score") == 78
        return b"%PDF-1.4"

    monkeypatch.setattr(export_processor, "build_pdf", fake_build_pdf)
    monkeypatch.setattr(export_processor, "build_csv", lambda packet: b"type,id\n")
    monkeypatch.setattr(
        export_processor,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "AUDIT_PACKET_MAX_EVIDENCE_FILES": 200,
                "AUDIT_PACKET_MAX_TOTAL_BYTES": 52_428_800,
                "AUDIT_PACKET_MAX_FILE_BYTES": 10_485_760,
                "EVIDENCE_BUCKET_NAME": "evidence",
            },
        )(),
    )

    processor = export_processor.ExportProcessor(
        access_token="service-role-123",
        bucket_name="exports",
    )
    processed = asyncio.run(processor.process_queued_exports_once(limit=3))

    assert processed == 1
    assert len(uploaded) == 1
    assert uploaded[0][0] == "exports"
    assert uploaded[0][1] == f"org/{ORG_ID}/exports/{EXPORT_ID}.zip"
    assert uploaded[0][3] == "application/zip"

    names = _zip_names(uploaded[0][2])
    assert "audit_report.pdf" in names
    assert "audit_data.csv" in names
    assert "manifest.json" in names
    assert any(name.startswith("evidence/") for name in names)
    manifest = _zip_json(uploaded[0][2], "manifest.json")
    readiness = manifest.get("readiness")
    assert isinstance(readiness, dict)
    assert readiness.get("score") == 78


def test_zip_export_processor_skips_evidence_when_limits_exceeded(monkeypatch) -> None:
    uploaded: list[bytes] = []

    async def fake_select_queued(limit: int = 3) -> list[dict[str, object]]:
        return [
            {
                "id": EXPORT_ID,
                "org_id": ORG_ID,
                "format": "zip",
                "scope": {},
                "status": "queued",
                "attempts": 0,
            }
        ]

    async def fake_select_packet(
        access_token: str, org_id: str, from_ts: str | None, to_ts: str | None
    ) -> dict[str, object]:
        return {
            "org_id": ORG_ID,
            "findings": [],
            "alerts": [],
            "tasks": [{"id": TASK_ID}],
            "task_evidence": [],
            "evidence_files": [
                {
                    "id": EVIDENCE_ID_1,
                    "task_id": TASK_ID,
                    "filename": "file-1.txt",
                    "storage_bucket": "evidence",
                    "storage_path": "orgs/a/tasks/t/file-1.txt",
                    "created_at": "2026-02-10T00:00:00Z",
                },
                {
                    "id": EVIDENCE_ID_2,
                    "task_id": TASK_ID,
                    "filename": "file-2.txt",
                    "storage_bucket": "evidence",
                    "storage_path": "orgs/a/tasks/t/file-2.txt",
                    "created_at": "2026-02-10T00:00:01Z",
                },
            ],
            "task_comments": [],
            "runs": [],
            "snapshots": [],
            "audit_timeline": [],
            "readiness_summary": {
                "id": "77777777-7777-7777-7777-777777777777",
                "org_id": ORG_ID,
                "computed_at": "2026-02-13T00:00:00Z",
                "score": 62,
                "controls_total": 10,
                "controls_with_evidence": 6,
                "evidence_items_total": 20,
                "evidence_items_done": 12,
                "open_alerts_high": 1,
                "open_tasks": 4,
                "overdue_tasks": 2,
                "metadata": {},
            },
            "finding_explanations": [],
            "row_count": 2,
        }

    async def fake_update_status(
        export_id: str,
        status_value: str,
        file_path: str | None,
        file_sha256: str | None,
        error_text: str | None,
        completed_at: str | None,
    ) -> None:
        return None

    async def fake_download_bytes(bucket: str, path: str) -> bytes:
        return b"12345678"

    async def fake_mark_started(export_id: str, attempts: int) -> None:
        assert export_id == EXPORT_ID
        assert attempts == 1

    async def fake_upload_bytes(bucket: str, path: str, data: bytes, content_type: str) -> None:
        uploaded.append(data)

    monkeypatch.setattr(export_processor, "select_queued_audit_exports_service", fake_select_queued)
    monkeypatch.setattr(export_processor, "select_audit_packet_data", fake_select_packet)
    monkeypatch.setattr(export_processor, "mark_audit_export_attempt_started", fake_mark_started)
    monkeypatch.setattr(export_processor, "update_audit_export_status", fake_update_status)
    monkeypatch.setattr(export_processor, "download_bytes", fake_download_bytes)
    monkeypatch.setattr(export_processor, "upload_bytes", fake_upload_bytes)
    monkeypatch.setattr(export_processor, "build_pdf", lambda packet: b"%PDF-1.4")
    monkeypatch.setattr(export_processor, "build_csv", lambda packet: b"type,id\n")
    monkeypatch.setattr(
        export_processor,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "AUDIT_PACKET_MAX_EVIDENCE_FILES": 200,
                "AUDIT_PACKET_MAX_TOTAL_BYTES": 10,
                "AUDIT_PACKET_MAX_FILE_BYTES": 10_485_760,
                "EVIDENCE_BUCKET_NAME": "evidence",
            },
        )(),
    )

    processor = export_processor.ExportProcessor(
        access_token="service-role-123",
        bucket_name="exports",
    )
    processed = asyncio.run(processor.process_queued_exports_once(limit=3))

    assert processed == 1
    assert len(uploaded) == 1
    manifest = _zip_json(uploaded[0], "manifest.json")
    warnings = manifest.get("warnings")
    assert isinstance(warnings, list)
    assert len(warnings) >= 1
    assert any("max total evidence bytes reached" in str(item).lower() for item in warnings)
    readiness = manifest.get("readiness")
    assert isinstance(readiness, dict)
    assert readiness.get("score") == 62
