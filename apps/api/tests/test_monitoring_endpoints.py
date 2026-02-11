from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.endpoints import monitoring as monitoring_endpoint
from app.core import supabase_rest
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
SOURCE_ID = "22222222-2222-2222-2222-222222222222"
RUN_ID = "33333333-3333-3333-3333-333333333333"
FINDING_ID = "44444444-4444-4444-4444-444444444444"
ALERT_ID = "55555555-5555-5555-5555-555555555555"
USER_ID = "66666666-6666-6666-6666-666666666666"


def test_findings_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/findings", params={"org_id": ORG_ID})
    assert response.status_code == 401


def test_findings_returns_list_when_supabase_ok(monkeypatch) -> None:
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
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"

            if url == "https://example.supabase.co/rest/v1/findings":
                assert params == {
                    "select": "id,org_id,source_id,run_id,title,summary,severity,detected_at,fingerprint,raw_url,raw_hash",
                    "org_id": f"eq.{ORG_ID}",
                    "order": "detected_at.desc",
                }
                return FakeResponse(
                    [
                        {
                            "id": FINDING_ID,
                            "org_id": ORG_ID,
                            "source_id": SOURCE_ID,
                            "run_id": RUN_ID,
                            "title": "TLS cert changed",
                            "summary": "Certificate rotated outside maintenance window.",
                            "severity": "high",
                            "detected_at": "2026-02-09T00:00:00Z",
                            "fingerprint": "sha256:abc",
                            "raw_url": "https://example.com",
                            "raw_hash": "abc123",
                        }
                    ]
                )

            if url == "https://example.supabase.co/rest/v1/finding_explanations":
                assert params == {
                    "select": "finding_id",
                    "org_id": f"eq.{ORG_ID}",
                }
                return FakeResponse([{"finding_id": FINDING_ID}])

            raise AssertionError(f"unexpected URL: {url}")

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in findings GET test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": USER_ID}
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/findings", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "findings": [
            {
                "id": FINDING_ID,
                "org_id": ORG_ID,
                "source_id": SOURCE_ID,
                "run_id": RUN_ID,
                "title": "TLS cert changed",
                "summary": "Certificate rotated outside maintenance window.",
                "severity": "high",
                "detected_at": "2026-02-09T00:00:00Z",
                "fingerprint": "sha256:abc",
                "raw_url": "https://example.com",
                "raw_hash": "abc123",
                "has_explanation": True,
            }
        ]
    }


def test_finding_explanation_returns_latest_record(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/finding_explanations"
            assert params == {
                "select": "id,org_id,finding_id,summary,diff_preview,citations,created_at",
                "finding_id": f"eq.{FINDING_ID}",
                "order": "created_at.desc",
                "limit": "1",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [
                    {
                        "id": "77777777-7777-7777-7777-777777777777",
                        "org_id": ORG_ID,
                        "finding_id": FINDING_ID,
                        "summary": "Source content changed in one section.",
                        "diff_preview": "@@ -1,2 +1,2 @@",
                        "citations": [{"quote": "new clause", "context": "@@ -1,2 +1,2 @@"}],
                        "created_at": "2026-02-11T00:00:00Z",
                    }
                ]
            )

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in finding explanation GET test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": USER_ID}
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/findings/{FINDING_ID}/explanation")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": "77777777-7777-7777-7777-777777777777",
        "org_id": ORG_ID,
        "finding_id": FINDING_ID,
        "summary": "Source content changed in one section.",
        "diff_preview": "@@ -1,2 +1,2 @@",
        "citations": [{"quote": "new clause", "context": "@@ -1,2 +1,2 @@"}],
        "created_at": "2026-02-11T00:00:00Z",
    }


def test_alerts_returns_list_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/alerts"
            assert params == {
                "select": "id,org_id,finding_id,status,owner_user_id,created_at,resolved_at",
                "org_id": f"eq.{ORG_ID}",
                "order": "created_at.desc",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [
                    {
                        "id": ALERT_ID,
                        "org_id": ORG_ID,
                        "finding_id": FINDING_ID,
                        "status": "open",
                        "owner_user_id": None,
                        "created_at": "2026-02-09T00:00:00Z",
                        "resolved_at": None,
                    }
                ]
            )

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in alerts GET test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": USER_ID}
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/alerts", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "alerts": [
            {
                "id": ALERT_ID,
                "org_id": ORG_ID,
                "finding_id": FINDING_ID,
                "status": "open",
                "owner_user_id": None,
                "created_at": "2026-02-09T00:00:00Z",
                "resolved_at": None,
            }
        ]
    }


def test_update_alert_calls_rpc(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/rpc/set_alert_status"
            assert json == {"p_alert_id": ALERT_ID, "p_status": "acknowledged"}
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse()

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in patch alert test")

    monkeypatch.setattr(
        monitoring_endpoint,
        "get_settings",
        lambda: SimpleNamespace(REQUIRE_ALERT_EVIDENCE_FOR_RESOLVE=False, ALERT_RESOLVE_MIN_EVIDENCE=1),
    )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": USER_ID}
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.patch(f"/api/v1/alerts/{ALERT_ID}", json={"status": "acknowledged"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_update_alert_requires_evidence_when_enabled(monkeypatch) -> None:
    async def fake_select_tasks_for_alert(access_token: str, alert_id: str) -> list[dict[str, str]]:
        assert access_token == "token-123"
        assert alert_id == ALERT_ID
        return [{"id": "99999999-9999-9999-9999-999999999999"}]

    async def fake_select_task_evidence(access_token: str, task_id: str) -> list[dict[str, str]]:
        assert access_token == "token-123"
        assert task_id == "99999999-9999-9999-9999-999999999999"
        return []

    monkeypatch.setattr(
        monitoring_endpoint,
        "get_settings",
        lambda: SimpleNamespace(REQUIRE_ALERT_EVIDENCE_FOR_RESOLVE=True, ALERT_RESOLVE_MIN_EVIDENCE=1),
    )
    monkeypatch.setattr(monitoring_endpoint, "select_tasks_for_alert", fake_select_tasks_for_alert)
    monkeypatch.setattr(monitoring_endpoint, "select_task_evidence", fake_select_task_evidence)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": USER_ID}
    )

    try:
        client = TestClient(app)
        response = client.patch(f"/api/v1/alerts/{ALERT_ID}", json={"status": "resolved"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Add evidence to a remediation task before resolving this alert."


def test_audit_returns_list_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/audit_log"
            assert params == {
                "select": "id,org_id,actor_user_id,action,entity_type,entity_id,metadata,created_at",
                "org_id": f"eq.{ORG_ID}",
                "order": "created_at.desc",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [
                    {
                        "id": "77777777-7777-7777-7777-777777777777",
                        "org_id": ORG_ID,
                        "actor_user_id": USER_ID,
                        "action": "monitor_run_queued",
                        "entity_type": "monitor_run",
                        "entity_id": RUN_ID,
                        "metadata": {"source_id": SOURCE_ID},
                        "created_at": "2026-02-09T00:00:00Z",
                    }
                ]
            )

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in audit GET test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": USER_ID}
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/audit", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "audit": [
            {
                "id": "77777777-7777-7777-7777-777777777777",
                "org_id": ORG_ID,
                "actor_user_id": USER_ID,
                "action": "monitor_run_queued",
                "entity_type": "monitor_run",
                "entity_id": RUN_ID,
                "metadata": {"source_id": SOURCE_ID},
                "created_at": "2026-02-09T00:00:00Z",
            }
        ]
    }


def test_monitor_runs_returns_list_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/monitor_runs"
            assert params == {
                "select": "id,org_id,source_id,status,started_at,finished_at,error,created_at",
                "org_id": f"eq.{ORG_ID}",
                "order": "created_at.desc",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [
                    {
                        "id": RUN_ID,
                        "org_id": ORG_ID,
                        "source_id": SOURCE_ID,
                        "status": "queued",
                        "started_at": None,
                        "finished_at": None,
                        "error": None,
                        "created_at": "2026-02-09T00:00:00Z",
                    }
                ]
            )

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in monitor runs GET test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": USER_ID}
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/monitor/runs", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "runs": [
            {
                "id": RUN_ID,
                "org_id": ORG_ID,
                "source_id": SOURCE_ID,
                "status": "queued",
                "started_at": None,
                "finished_at": None,
                "error": None,
                "created_at": "2026-02-09T00:00:00Z",
            }
        ]
    }


def test_monitor_run_queues_only(monkeypatch) -> None:
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
            self.create_run_called = False
            self.audit_called = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, object], headers: dict[str, str]) -> FakeResponse:
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"

            if url.endswith("/rpc/create_monitor_run"):
                self.create_run_called = True
                assert json == {"p_org_id": ORG_ID, "p_source_id": SOURCE_ID}
                return FakeResponse(RUN_ID)

            if url.endswith("/rpc/append_audit"):
                self.audit_called = True
                assert json == {
                    "p_org_id": ORG_ID,
                    "p_action": "monitor_run_queued",
                    "p_entity_type": "monitor_run",
                    "p_entity_id": RUN_ID,
                    "p_metadata": {"source_id": SOURCE_ID},
                }
                return FakeResponse()

            raise AssertionError(f"Unexpected URL called: {url}")

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in monitor run test")

    monkeypatch.setattr(
        monitoring_endpoint,
        "get_settings",
        lambda: SimpleNamespace(
            REQUIRE_ALERT_EVIDENCE_FOR_RESOLVE=True,
            ALERT_RESOLVE_MIN_EVIDENCE=1,
        ),
    )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": USER_ID}
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/monitor/run",
            json={
                "org_id": ORG_ID,
                "source_id": SOURCE_ID,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": RUN_ID, "status": "queued"}
