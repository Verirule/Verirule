from fastapi.testclient import TestClient

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
                "select": "id,org_id,name,type,url,is_enabled,created_at",
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
                        "url": "https://example.com/feed.xml",
                        "is_enabled": True,
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
                "url": "https://example.com/feed.xml",
                "is_enabled": True,
                "created_at": "2026-02-09T00:00:00Z",
            }
        ]
    }


def test_create_source_returns_id_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/rpc/create_source"
            assert json == {
                "p_org_id": "11111111-1111-1111-1111-111111111111",
                "p_name": "Security RSS",
                "p_type": "rss",
                "p_url": "https://example.com/feed.xml",
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

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sources",
            json={
                "org_id": "11111111-1111-1111-1111-111111111111",
                "name": "Security RSS",
                "type": "rss",
                "url": "https://example.com/feed.xml",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": "22222222-2222-2222-2222-222222222222"}


def test_toggle_source_returns_ok_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/rpc/toggle_source"
            assert json == {
                "p_source_id": "22222222-2222-2222-2222-222222222222",
                "p_is_enabled": False,
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse()

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in toggle_source test")

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
