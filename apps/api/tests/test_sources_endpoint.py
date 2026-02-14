from fastapi.testclient import TestClient

from app.api.v1.endpoints import sources as sources_endpoint
from app.billing import guard as billing_guard
from app.core import supabase_rest
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app


def test_sources_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/sources", params={"org_id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01"})
    assert response.status_code == 401


def test_sources_returns_list_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/sources"
            assert params == {
                "select": "id,org_id,name,type,kind,config,title,url,is_enabled,cadence,next_run_at,last_run_at,created_at",
                "org_id": "eq.11111111-1111-1111-1111-111111111111",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [
                    {
                        "id": "22222222-2222-2222-2222-222222222222",
                        "org_id": "11111111-1111-1111-1111-111111111111",
                        "name": "Security RSS",
                        "type": "rss",
                        "kind": "rss",
                        "config": {},
                        "title": "Security Feed",
                        "url": "https://example.com/feed.xml",
                        "is_enabled": True,
                        "cadence": "manual",
                        "next_run_at": None,
                        "last_run_at": None,
                        "created_at": "2026-02-09T00:00:00Z",
                    }
                ]
            )

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in sources GET test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/sources", params={"org_id": "11111111-1111-1111-1111-111111111111"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "sources": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "org_id": "11111111-1111-1111-1111-111111111111",
                "name": "Security RSS",
                "type": "rss",
                "kind": "rss",
                "config": {},
                "title": "Security Feed",
                "url": "https://example.com/feed.xml",
                "is_enabled": True,
                "cadence": "manual",
                "next_run_at": None,
                "last_run_at": None,
                "created_at": "2026-02-09T00:00:00Z",
            }
        ]
    }


def test_create_source_returns_id_when_supabase_ok(monkeypatch) -> None:
    async def fake_select_org_billing(access_token: str, org_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert org_id == "11111111-1111-1111-1111-111111111111"
        return {"id": org_id, "plan": "pro"}

    async def fake_select_sources(access_token: str, org_id: str) -> list[dict[str, object]]:
        assert access_token == "token-123"
        assert org_id == "11111111-1111-1111-1111-111111111111"
        return []

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
            assert url == "https://example.supabase.co/rest/v1/rpc/create_source_v2"
            assert json == {
                "p_org_id": "11111111-1111-1111-1111-111111111111",
                "p_name": "Security RSS",
                "p_type": "rss",
                "p_url": "https://example.com/feed.xml",
                "p_kind": "rss",
                "p_config": {},
                "p_title": "Security Feed",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse("22222222-2222-2222-2222-222222222222")

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in create_source test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(sources_endpoint, "select_org_billing", fake_select_org_billing)
    monkeypatch.setattr(sources_endpoint, "select_sources", fake_select_sources)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sources",
            json={
                "org_id": "11111111-1111-1111-1111-111111111111",
                "name": "Security RSS",
                "type": "rss",
                "url": "https://example.com/feed.xml",
                "kind": "rss",
                "config": {},
                "title": "Security Feed",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": "22222222-2222-2222-2222-222222222222"}


def test_create_source_returns_402_when_limit_reached(monkeypatch) -> None:
    async def fake_select_org_billing(access_token: str, org_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert org_id == "11111111-1111-1111-1111-111111111111"
        return {"id": org_id, "plan": "free"}

    async def fake_select_sources(access_token: str, org_id: str) -> list[dict[str, object]]:
        assert access_token == "token-123"
        assert org_id == "11111111-1111-1111-1111-111111111111"
        return [{"id": "1"}, {"id": "2"}, {"id": "3"}]

    async def fail_create_source(*args, **kwargs):  # pragma: no cover
        raise AssertionError("create_source RPC should not run when source limit is reached")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(sources_endpoint, "select_org_billing", fake_select_org_billing)
    monkeypatch.setattr(sources_endpoint, "select_sources", fake_select_sources)
    monkeypatch.setattr(sources_endpoint, "rpc_create_source", fail_create_source)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sources",
            json={
                "org_id": "11111111-1111-1111-1111-111111111111",
                "name": "Security RSS",
                "type": "rss",
                "url": "https://example.com/feed.xml",
                "kind": "rss",
                "config": {},
                "title": "Security Feed",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 402
    assert response.json() == {"detail": "Source limit reached (3). Upgrade required."}


def test_update_source_returns_ok_when_supabase_ok(monkeypatch) -> None:
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

        async def post(self, url: str, json: dict[str, object], headers: dict[str, str]) -> FakeResponse:
            assert url == "https://example.supabase.co/rest/v1/rpc/update_source"
            assert json == {
                "p_source_id": "22222222-2222-2222-2222-222222222222",
                "p_name": None,
                "p_url": None,
                "p_type": None,
                "p_kind": None,
                "p_config": None,
                "p_title": None,
                "p_is_enabled": False,
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse()

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in update_source test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.patch(
            "/api/v1/sources/22222222-2222-2222-2222-222222222222",
            json={"is_enabled": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_due_sources_returns_list_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/sources"
            assert params == {
                "select": "id,org_id,name,type,kind,config,title,url,is_enabled,cadence,next_run_at,last_run_at,created_at",
                "cadence": "neq.manual",
                "is_enabled": "eq.true",
                "next_run_at": "lte.now()",
                "order": "next_run_at.asc",
                "org_id": "eq.11111111-1111-1111-1111-111111111111",
            }
            assert headers["Authorization"] == "Bearer token-123"
            return FakeResponse(
                [
                    {
                        "id": "22222222-2222-2222-2222-222222222222",
                        "org_id": "11111111-1111-1111-1111-111111111111",
                        "name": "Security RSS",
                        "type": "rss",
                        "kind": "rss",
                        "config": {},
                        "title": None,
                        "url": "https://example.com/feed.xml",
                        "is_enabled": True,
                        "cadence": "hourly",
                        "next_run_at": "2026-02-11T00:00:00Z",
                        "last_run_at": "2026-02-10T23:00:00Z",
                        "created_at": "2026-02-09T00:00:00Z",
                    }
                ]
            )

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in due_sources test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/sources/due", params={"org_id": "11111111-1111-1111-1111-111111111111"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "sources": [
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "org_id": "11111111-1111-1111-1111-111111111111",
                "name": "Security RSS",
                "type": "rss",
                "kind": "rss",
                "config": {},
                "title": None,
                "url": "https://example.com/feed.xml",
                "is_enabled": True,
                "cadence": "hourly",
                "next_run_at": "2026-02-11T00:00:00Z",
                "last_run_at": "2026-02-10T23:00:00Z",
                "created_at": "2026-02-09T00:00:00Z",
            }
        ]
    }


def test_schedule_source_returns_ok_when_supabase_ok(monkeypatch) -> None:
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

        async def post(self, url: str, json: dict[str, object], headers: dict[str, str]) -> FakeResponse:
            assert headers["Authorization"] == "Bearer token-123"
            if url == "https://example.supabase.co/rest/v1/rpc/set_source_cadence":
                assert json == {
                    "p_source_id": "22222222-2222-2222-2222-222222222222",
                    "p_cadence": "hourly",
                }
                return FakeResponse()

            if url == "https://example.supabase.co/rest/v1/rpc/schedule_next_run":
                assert json == {"p_source_id": "22222222-2222-2222-2222-222222222222"}
                return FakeResponse()

            raise AssertionError(f"unexpected URL in schedule_source test: {url}")

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in schedule_source test")

    async def fake_select_source_by_id(access_token: str, source_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert source_id == "22222222-2222-2222-2222-222222222222"
        return {"id": source_id, "org_id": "11111111-1111-1111-1111-111111111111"}

    async def fake_select_org_billing(access_token: str, org_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert org_id == "11111111-1111-1111-1111-111111111111"
        return {"id": org_id, "plan": "pro"}

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(billing_guard, "select_source_by_id", fake_select_source_by_id)
    monkeypatch.setattr(billing_guard, "select_org_billing", fake_select_org_billing)

    try:
        client = TestClient(app)
        response = client.patch(
            "/api/v1/sources/22222222-2222-2222-2222-222222222222/schedule",
            json={"cadence": "hourly"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_create_source_validates_github_repo_config() -> None:
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sources",
            json={
                "org_id": "11111111-1111-1111-1111-111111111111",
                "name": "OpenAI Releases",
                "kind": "github_releases",
                "url": "https://github.com/openai/openai-python/releases",
                "config": {},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
