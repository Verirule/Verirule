import asyncio

import httpx
from fastapi.testclient import TestClient

from app.api.v1.endpoints import orgs as orgs_endpoint
from app.core import supabase_rest
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app


def test_orgs_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/orgs")
    assert response.status_code == 401


def test_create_org_requires_token() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/orgs", json={"name": "Acme"})
    assert response.status_code == 401


def test_orgs_returns_list_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/orgs"
            assert params == {"select": "id,name,created_at"}
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [{"id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01", "name": "Acme", "created_at": "2026-02-09T00:00:00Z"}]
            )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/orgs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "orgs": [{"id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01", "name": "Acme", "created_at": "2026-02-09T00:00:00Z"}]
    }


def test_orgs_mine_returns_list_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/orgs"
            assert params == {"select": "id,name,created_at"}
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [{"id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01", "name": "Acme", "created_at": "2026-02-09T00:00:00Z"}]
            )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/orgs/mine")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "orgs": [{"id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01", "name": "Acme", "created_at": "2026-02-09T00:00:00Z"}]
    }


def test_create_org_returns_id_when_supabase_ok(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/rpc/create_org"
            assert json == {"p_name": "Acme"}
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse("3e66f70d-1644-4b07-8d03-3dbfef9b3e01")

        async def get(self, url: str, params: dict[str, str], headers: dict[str, str]) -> FakeResponse:
            assert url == "https://example.supabase.co/rest/v1/orgs"
            assert params == {"select": "id,name,created_at"}
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse([])

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post("/api/v1/orgs", json={"name": "Acme"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01"}


def test_create_org_accepts_object_rpc_response(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/rpc/create_org"
            assert json == {"p_name": "Acme"}
            assert headers["Authorization"] == "Bearer token-123"
            return FakeResponse({"create_org": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01"})

        async def get(self, url: str, params: dict[str, str], headers: dict[str, str]) -> FakeResponse:
            assert url == "https://example.supabase.co/rest/v1/orgs"
            return FakeResponse([])

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post("/api/v1/orgs", json={"name": "Acme"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01"}


def test_create_org_is_idempotent_returns_existing_id(monkeypatch) -> None:
    async def fake_select_orgs(access_token: str) -> list[dict[str, str]]:
        assert access_token == "token-123"
        return [
            {
                "id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01",
                "name": "Acme",
                "created_at": "2026-02-09T00:00:00Z",
            }
        ]

    async def fail_create_org(access_token: str, name: str) -> str:  # pragma: no cover
        raise AssertionError("create_org RPC should not run when matching org already exists")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(orgs_endpoint, "supabase_select_orgs", fake_select_orgs)
    monkeypatch.setattr(orgs_endpoint, "supabase_rpc_create_org", fail_create_org)

    try:
        client = TestClient(app)
        response = client.post("/api/v1/orgs", json={"name": "  acme  "})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"id": "3e66f70d-1644-4b07-8d03-3dbfef9b3e01"}


def test_create_org_timeout_returns_504(monkeypatch) -> None:
    async def fake_select_orgs(access_token: str) -> list[dict[str, str]]:
        assert access_token == "token-123"
        return []

    async def fake_create_org(access_token: str, name: str) -> str:
        assert access_token == "token-123"
        assert name == "Acme"
        await asyncio.sleep(0.01)
        return "3e66f70d-1644-4b07-8d03-3dbfef9b3e01"

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(orgs_endpoint, "supabase_select_orgs", fake_select_orgs)
    monkeypatch.setattr(orgs_endpoint, "supabase_rpc_create_org", fake_create_org)
    monkeypatch.setattr(orgs_endpoint, "ORG_CREATE_TIMEOUT_SECONDS", 0.001)

    try:
        client = TestClient(app)
        response = client.post("/api/v1/orgs", json={"name": "Acme"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 504
    payload = response.json()
    assert payload["detail"]["message"] == "Workspace creation timed out. Please try again."
    assert isinstance(payload["detail"]["request_id"], str)
    assert payload["detail"]["request_id"]


def test_create_org_supabase_timeout_returns_502_with_safe_message(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, params: dict[str, str], headers: dict[str, str]):
            raise httpx.ReadTimeout("timed out")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post("/api/v1/orgs", json={"name": "Acme"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    payload = response.json()
    assert payload["detail"]["message"] == "Failed to fetch organizations from Supabase."
    assert isinstance(payload["detail"]["request_id"], str)
    assert payload["detail"]["request_id"]
