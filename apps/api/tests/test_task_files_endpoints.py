import re

from fastapi.testclient import TestClient

from app.api.v1.endpoints import task_files
from app.core import supabase_storage
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

TASK_ID = "22222222-2222-2222-2222-222222222222"
ORG_ID = "11111111-1111-1111-1111-111111111111"
EVIDENCE_ID = "33333333-3333-3333-3333-333333333333"


def test_upload_url_requires_token() -> None:
    client = TestClient(app)
    response = client.post(f"/api/v1/tasks/{TASK_ID}/evidence/upload-url", json={"filename": "report.pdf"})
    assert response.status_code == 401


def test_upload_url_returns_404_when_task_not_visible(monkeypatch) -> None:
    async def fake_select_task_by_id(access_token: str, task_id: str) -> None:
        assert access_token == "token-123"
        assert task_id == TASK_ID
        return None

    monkeypatch.setattr(task_files, "select_task_by_id", fake_select_task_by_id)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/tasks/{TASK_ID}/evidence/upload-url",
            json={"filename": "report.pdf"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found."}


def test_upload_url_returns_501_when_service_role_missing(monkeypatch) -> None:
    async def fake_select_task_by_id(access_token: str, task_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert task_id == TASK_ID
        return {"id": TASK_ID, "org_id": ORG_ID}

    monkeypatch.setattr(task_files, "select_task_by_id", fake_select_task_by_id)
    monkeypatch.setattr(
        supabase_storage,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {"SUPABASE_SERVICE_ROLE_KEY": None, "SUPABASE_URL": "https://example.supabase.co"},
        )(),
    )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/tasks/{TASK_ID}/evidence/upload-url",
            json={"filename": "report.pdf"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 501
    assert response.json() == {"detail": "File evidence uploads are not configured."}


def test_upload_url_sanitizes_filename_and_returns_signed_url(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, int], headers: dict[str, str]) -> FakeResponse:
            assert json == {"expiresIn": 300}
            assert headers["Authorization"] == "Bearer service-role-123"
            assert headers["apikey"] == "service-role-123"
            assert re.search(
                rf"/storage/v1/object/sign/evidence/org/{ORG_ID}/tasks/{TASK_ID}/[0-9a-f-]{{36}}-quarterly_audit_2026_\.pdf$",
                url,
            )
            return FakeResponse({"signedURL": "/storage/v1/object/sign/evidence/signed-object?token=abc"})

    async def fake_select_task_by_id(access_token: str, task_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert task_id == TASK_ID
        return {"id": TASK_ID, "org_id": ORG_ID}

    monkeypatch.setattr(task_files, "select_task_by_id", fake_select_task_by_id)
    monkeypatch.setattr(
        supabase_storage,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "SUPABASE_SERVICE_ROLE_KEY": "service-role-123",
                "SUPABASE_URL": "https://example.supabase.co",
            },
        )(),
    )
    monkeypatch.setattr(supabase_storage.httpx, "AsyncClient", FakeAsyncClient)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/tasks/{TASK_ID}/evidence/upload-url",
            json={"filename": "..\\quarterly audit 2026!.pdf", "content_type": "application/pdf"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["expiresIn"] == 300
    assert payload["uploadUrl"] == "https://example.supabase.co/storage/v1/object/sign/evidence/signed-object?token=abc"
    assert re.match(
        rf"^org/{ORG_ID}/tasks/{TASK_ID}/[0-9a-f-]{{36}}-quarterly_audit_2026_\.pdf$",
        payload["path"],
    )


def test_download_url_returns_signed_url(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, int], headers: dict[str, str]) -> FakeResponse:
            assert json == {"expiresIn": 300}
            assert headers["Authorization"] == "Bearer service-role-123"
            assert headers["apikey"] == "service-role-123"
            assert url.endswith(
                f"/storage/v1/object/sign/evidence/org/{ORG_ID}/tasks/{TASK_ID}/proof.txt"
            )
            return FakeResponse({"signedURL": "/storage/v1/object/sign/evidence/proof.txt?token=xyz"})

    async def fake_select_task_by_id(access_token: str, task_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert task_id == TASK_ID
        return {"id": TASK_ID, "org_id": ORG_ID}

    async def fake_select_task_evidence_by_id(
        access_token: str, task_id: str, evidence_id: str
    ) -> dict[str, str]:
        assert access_token == "token-123"
        assert task_id == TASK_ID
        assert evidence_id == EVIDENCE_ID
        return {
            "id": EVIDENCE_ID,
            "task_id": TASK_ID,
            "type": "file",
            "ref": f"org/{ORG_ID}/tasks/{TASK_ID}/proof.txt",
        }

    monkeypatch.setattr(task_files, "select_task_by_id", fake_select_task_by_id)
    monkeypatch.setattr(task_files, "select_task_evidence_by_id", fake_select_task_evidence_by_id)
    monkeypatch.setattr(
        supabase_storage,
        "get_settings",
        lambda: type(
            "Settings",
            (),
            {
                "SUPABASE_SERVICE_ROLE_KEY": "service-role-123",
                "SUPABASE_URL": "https://example.supabase.co",
            },
        )(),
    )
    monkeypatch.setattr(supabase_storage.httpx, "AsyncClient", FakeAsyncClient)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/tasks/{TASK_ID}/evidence/{EVIDENCE_ID}/download-url")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "downloadUrl": "https://example.supabase.co/storage/v1/object/sign/evidence/proof.txt?token=xyz",
        "expiresIn": 300,
    }
