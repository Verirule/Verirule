from fastapi.testclient import TestClient

from app.api.v1.endpoints import evidence_files
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

TASK_ID = "22222222-2222-2222-2222-222222222222"
ORG_ID = "11111111-1111-1111-1111-111111111111"
EVIDENCE_FILE_ID = "33333333-3333-3333-3333-333333333333"
USER_ID = "44444444-4444-4444-4444-444444444444"


def test_upload_url_rejects_oversized_file(monkeypatch) -> None:
    async def fake_select_task_by_id(access_token: str, task_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert task_id == TASK_ID
        return {"id": TASK_ID, "org_id": ORG_ID}

    monkeypatch.setattr(evidence_files, "select_task_by_id", fake_select_task_by_id)
    monkeypatch.setattr(
        evidence_files,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "MAX_EVIDENCE_UPLOAD_BYTES": 10,
                "EVIDENCE_BUCKET_NAME": "evidence",
                "EVIDENCE_SIGNED_URL_SECONDS": 900,
            },
        )(),
    )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": USER_ID},
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/tasks/{TASK_ID}/evidence-files/upload-url",
            json={
                "org_id": ORG_ID,
                "filename": "proof.pdf",
                "content_type": "application/pdf",
                "byte_size": 11,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 413
    assert response.json() == {"detail": "Evidence file exceeds maximum upload size."}


def test_finalize_updates_hash_and_records_audit_event(monkeypatch) -> None:
    finalized_calls: list[dict[str, str]] = []
    audit_calls: list[dict[str, object]] = []

    async def fake_select_evidence_file_by_id(
        access_token: str, evidence_file_id: str, org_id: str
    ) -> dict[str, str]:
        assert access_token == "token-123"
        assert evidence_file_id == EVIDENCE_FILE_ID
        assert org_id == ORG_ID
        return {
            "id": EVIDENCE_FILE_ID,
            "org_id": ORG_ID,
            "task_id": TASK_ID,
            "filename": "proof.pdf",
            "storage_bucket": "evidence",
            "storage_path": f"orgs/{ORG_ID}/tasks/{TASK_ID}/abc_proof.pdf",
            "content_type": "application/pdf",
            "byte_size": 123,
            "sha256": None,
            "uploaded_by": None,
            "created_at": "2026-02-01T00:00:00Z",
        }

    async def fake_finalize_service(
        evidence_file_id: str, org_id: str, sha256: str, uploaded_by: str
    ) -> dict[str, object]:
        finalized_calls.append(
            {
                "evidence_file_id": evidence_file_id,
                "org_id": org_id,
                "sha256": sha256,
                "uploaded_by": uploaded_by,
            }
        )
        return {
            "id": EVIDENCE_FILE_ID,
            "org_id": ORG_ID,
            "task_id": TASK_ID,
            "filename": "proof.pdf",
            "storage_bucket": "evidence",
            "storage_path": f"orgs/{ORG_ID}/tasks/{TASK_ID}/abc_proof.pdf",
            "content_type": "application/pdf",
            "byte_size": 123,
            "sha256": sha256,
            "uploaded_by": uploaded_by,
            "created_at": "2026-02-01T00:00:00Z",
        }

    async def fake_record_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "token-123"
        audit_calls.append(payload)

    monkeypatch.setattr(
        evidence_files, "select_evidence_file_by_id", fake_select_evidence_file_by_id
    )
    monkeypatch.setattr(evidence_files, "update_evidence_file_finalize_service", fake_finalize_service)
    monkeypatch.setattr(evidence_files, "rpc_record_audit_event", fake_record_audit)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": USER_ID},
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/evidence-files/{EVIDENCE_FILE_ID}/finalize",
            json={
                "org_id": ORG_ID,
                "sha256": "a" * 64,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert finalized_calls == [
        {
            "evidence_file_id": EVIDENCE_FILE_ID,
            "org_id": ORG_ID,
            "sha256": "a" * 64,
            "uploaded_by": USER_ID,
        }
    ]
    assert len(audit_calls) == 1
    assert audit_calls[0]["p_action"] == "evidence_uploaded"
    assert audit_calls[0]["p_entity_type"] == "evidence_file"
    assert audit_calls[0]["p_entity_id"] == EVIDENCE_FILE_ID


def test_download_url_returns_signed_url(monkeypatch) -> None:
    async def fake_select_evidence_file_by_id(
        access_token: str, evidence_file_id: str, org_id: str
    ) -> dict[str, str]:
        assert access_token == "token-123"
        assert evidence_file_id == EVIDENCE_FILE_ID
        assert org_id == ORG_ID
        return {
            "id": EVIDENCE_FILE_ID,
            "org_id": ORG_ID,
            "task_id": TASK_ID,
            "filename": "proof.pdf",
            "storage_bucket": "evidence",
            "storage_path": f"orgs/{ORG_ID}/tasks/{TASK_ID}/abc_proof.pdf",
            "content_type": "application/pdf",
            "byte_size": 123,
            "sha256": "a" * 64,
            "uploaded_by": USER_ID,
            "created_at": "2026-02-01T00:00:00Z",
        }

    async def fake_signed_download(bucket: str, path: str, expires: int) -> dict[str, str]:
        assert bucket == "evidence"
        assert path == f"orgs/{ORG_ID}/tasks/{TASK_ID}/abc_proof.pdf"
        assert expires == 900
        return {"path": path, "signed_url": "https://example.supabase.co/storage/v1/object/sign/evidence/abc?token=1"}

    monkeypatch.setattr(
        evidence_files, "select_evidence_file_by_id", fake_select_evidence_file_by_id
    )
    monkeypatch.setattr(evidence_files, "create_signed_download_url", fake_signed_download)
    monkeypatch.setattr(
        evidence_files,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "EVIDENCE_SIGNED_URL_SECONDS": 900,
            },
        )(),
    )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": USER_ID},
    )

    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/evidence-files/{EVIDENCE_FILE_ID}/download-url",
            params={"org_id": ORG_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "download_url": "https://example.supabase.co/storage/v1/object/sign/evidence/abc?token=1",
        "expires_in": 900,
    }
