from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.endpoints import monitoring as monitoring_endpoint
from app.core import supabase_rest
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
TASK_ID = "22222222-2222-2222-2222-222222222222"
ALERT_ID = "33333333-3333-3333-3333-333333333333"
FINDING_ID = "44444444-4444-4444-4444-444444444444"


def test_tasks_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/tasks", params={"org_id": ORG_ID})
    assert response.status_code == 401


def test_tasks_list_returns_rows_when_supabase_ok(monkeypatch) -> None:
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

        async def get(self, url: str, params: dict[str, str], headers: dict[str, str]) -> FakeResponse:
            assert url == "https://example.supabase.co/rest/v1/tasks"
            assert params == {
                "select": "id,org_id,title,description,status,assignee_user_id,alert_id,finding_id,due_at,created_at,updated_at",
                "org_id": f"eq.{ORG_ID}",
                "order": "created_at.desc",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [
                    {
                        "id": TASK_ID,
                        "org_id": ORG_ID,
                        "title": "Investigate cert rotation",
                        "description": "Track remediation and evidence",
                        "status": "open",
                        "assignee_user_id": None,
                        "alert_id": ALERT_ID,
                        "finding_id": FINDING_ID,
                        "due_at": None,
                        "created_at": "2026-02-09T00:00:00Z",
                        "updated_at": "2026-02-09T00:00:00Z",
                    }
                ]
            )

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in list tasks test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/tasks", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "tasks": [
            {
                "id": TASK_ID,
                "org_id": ORG_ID,
                "title": "Investigate cert rotation",
                "description": "Track remediation and evidence",
                "status": "open",
                "assignee_user_id": None,
                "alert_id": ALERT_ID,
                "finding_id": FINDING_ID,
                "due_at": None,
                "created_at": "2026-02-09T00:00:00Z",
                "updated_at": "2026-02-09T00:00:00Z",
            }
        ]
    }


def test_create_task_returns_id_when_supabase_ok(monkeypatch) -> None:
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

        async def post(self, url: str, json: dict[str, str | None], headers: dict[str, str]) -> FakeResponse:
            assert url == "https://example.supabase.co/rest/v1/rpc/create_task"
            assert json == {
                "p_org_id": ORG_ID,
                "p_title": "Investigate cert rotation",
                "p_description": "Track remediation and evidence",
                "p_alert_id": ALERT_ID,
                "p_finding_id": FINDING_ID,
                "p_due_at": "2026-03-01T00:00:00+00:00",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(TASK_ID)

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in create task test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/tasks",
            json={
                "org_id": ORG_ID,
                "title": "Investigate cert rotation",
                "description": "Track remediation and evidence",
                "alert_id": ALERT_ID,
                "finding_id": FINDING_ID,
                "due_at": "2026-03-01T00:00:00Z",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": TASK_ID}


def test_alert_resolution_requires_evidence_when_none_exists(monkeypatch) -> None:
    async def fake_select_tasks_for_alert(access_token: str, alert_id: str) -> list[dict[str, str]]:
        assert access_token == "token-123"
        assert alert_id == ALERT_ID
        return [{"id": TASK_ID, "org_id": ORG_ID}]

    async def fake_select_task_evidence(access_token: str, task_id: str) -> list[dict[str, str]]:
        assert access_token == "token-123"
        assert task_id == TASK_ID
        return []

    async def fake_select_evidence_files_by_task(
        access_token: str, task_id: str, org_id: str
    ) -> list[dict[str, str]]:
        assert access_token == "token-123"
        assert task_id == TASK_ID
        assert org_id == ORG_ID
        return []

    monkeypatch.setattr(
        monitoring_endpoint,
        "get_settings",
        lambda: SimpleNamespace(REQUIRE_ALERT_EVIDENCE_FOR_RESOLVE=True, ALERT_RESOLVE_MIN_EVIDENCE=1),
    )
    monkeypatch.setattr(monitoring_endpoint, "select_tasks_for_alert", fake_select_tasks_for_alert)
    monkeypatch.setattr(monitoring_endpoint, "select_task_evidence", fake_select_task_evidence)
    monkeypatch.setattr(
        monitoring_endpoint, "select_evidence_files_by_task", fake_select_evidence_files_by_task
    )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": "user-1"}
    )

    try:
        client = TestClient(app)
        response = client.patch(f"/api/v1/alerts/{ALERT_ID}", json={"status": "resolved"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Add evidence to a remediation task before resolving this alert."
    }
