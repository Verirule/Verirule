from fastapi.testclient import TestClient

from app.core import supabase_rest
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
TASK_ID = "22222222-2222-2222-2222-222222222222"
ALERT_ID = "33333333-3333-3333-3333-333333333333"
FINDING_ID = "44444444-4444-4444-4444-444444444444"
ASSIGNEE_ID = "55555555-5555-5555-5555-555555555555"
COMMENT_ID = "66666666-6666-6666-6666-666666666666"
EVIDENCE_ID = "77777777-7777-7777-7777-777777777777"


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
                "select": "id,org_id,title,status,assignee_user_id,alert_id,finding_id,due_at,created_by_user_id,created_at",
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
                        "status": "open",
                        "assignee_user_id": None,
                        "alert_id": ALERT_ID,
                        "finding_id": FINDING_ID,
                        "due_at": None,
                        "created_by_user_id": ASSIGNEE_ID,
                        "created_at": "2026-02-09T00:00:00Z",
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
                "status": "open",
                "assignee_user_id": None,
                "alert_id": ALERT_ID,
                "finding_id": FINDING_ID,
                "due_at": None,
                "created_by_user_id": ASSIGNEE_ID,
                "created_at": "2026-02-09T00:00:00Z",
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

        async def post(self, url: str, json: dict[str, str], headers: dict[str, str]) -> FakeResponse:
            assert url == "https://example.supabase.co/rest/v1/rpc/create_task"
            assert json == {
                "p_org_id": ORG_ID,
                "p_title": "Investigate cert rotation",
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
                "alert_id": ALERT_ID,
                "finding_id": FINDING_ID,
                "due_at": "2026-03-01T00:00:00Z",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": TASK_ID}


def test_update_task_calls_assign_and_status_rpcs(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):  # pragma: no cover
            return None

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, str], headers: dict[str, str]) -> FakeResponse:
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            if url.endswith("/rpc/assign_task"):
                assert json == {"p_task_id": TASK_ID, "p_user_id": ASSIGNEE_ID}
                return FakeResponse()
            if url.endswith("/rpc/set_task_status"):
                assert json == {"p_task_id": TASK_ID, "p_status": "in_progress"}
                return FakeResponse()
            raise AssertionError(f"Unexpected URL called: {url}")

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in task update test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.patch(
            f"/api/v1/tasks/{TASK_ID}",
            json={"assignee_user_id": ASSIGNEE_ID, "status": "in_progress"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_task_comments_and_evidence_endpoints(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload=None):
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
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            if url.endswith("/rest/v1/task_comments"):
                assert params == {
                    "select": "id,task_id,author_user_id,body,created_at",
                    "task_id": f"eq.{TASK_ID}",
                    "order": "created_at.asc",
                }
                return FakeResponse(
                    [
                        {
                            "id": COMMENT_ID,
                            "task_id": TASK_ID,
                            "author_user_id": ASSIGNEE_ID,
                            "body": "Started investigating logs.",
                            "created_at": "2026-02-09T00:00:00Z",
                        }
                    ]
                )

            if url.endswith("/rest/v1/task_evidence"):
                assert params == {
                    "select": "id,task_id,type,ref,created_by_user_id,created_at",
                    "task_id": f"eq.{TASK_ID}",
                    "order": "created_at.asc",
                }
                return FakeResponse(
                    [
                        {
                            "id": EVIDENCE_ID,
                            "task_id": TASK_ID,
                            "type": "link",
                            "ref": "https://example.com/cert-diff",
                            "created_by_user_id": ASSIGNEE_ID,
                            "created_at": "2026-02-09T00:00:00Z",
                        }
                    ]
                )

            raise AssertionError(f"Unexpected URL called: {url}")

        async def post(self, url: str, json: dict[str, str], headers: dict[str, str]) -> FakeResponse:
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            if url.endswith("/rpc/add_task_comment"):
                assert json == {"p_task_id": TASK_ID, "p_body": "Need packet capture evidence."}
                return FakeResponse(COMMENT_ID)
            if url.endswith("/rpc/add_task_evidence"):
                assert json == {"p_task_id": TASK_ID, "p_type": "log", "p_ref": "sha256:log-entry"}
                return FakeResponse(EVIDENCE_ID)
            raise AssertionError(f"Unexpected URL called: {url}")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        comments_response = client.get(f"/api/v1/tasks/{TASK_ID}/comments")
        evidence_response = client.get(f"/api/v1/tasks/{TASK_ID}/evidence")
        add_comment_response = client.post(
            f"/api/v1/tasks/{TASK_ID}/comments",
            json={"body": "Need packet capture evidence."},
        )
        add_evidence_response = client.post(
            f"/api/v1/tasks/{TASK_ID}/evidence",
            json={"type": "log", "ref": "sha256:log-entry"},
        )
    finally:
        app.dependency_overrides.clear()

    assert comments_response.status_code == 200
    assert comments_response.json() == {
        "comments": [
            {
                "id": COMMENT_ID,
                "task_id": TASK_ID,
                "author_user_id": ASSIGNEE_ID,
                "body": "Started investigating logs.",
                "created_at": "2026-02-09T00:00:00Z",
            }
        ]
    }

    assert evidence_response.status_code == 200
    assert evidence_response.json() == {
        "evidence": [
            {
                "id": EVIDENCE_ID,
                "task_id": TASK_ID,
                "type": "link",
                "ref": "https://example.com/cert-diff",
                "created_by_user_id": ASSIGNEE_ID,
                "created_at": "2026-02-09T00:00:00Z",
            }
        ]
    }

    assert add_comment_response.status_code == 200
    assert add_comment_response.json() == {"id": COMMENT_ID}

    assert add_evidence_response.status_code == 200
    assert add_evidence_response.json() == {"id": EVIDENCE_ID}
