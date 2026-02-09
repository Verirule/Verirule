from fastapi.testclient import TestClient

from app.core import supabase_rest
from app.core.integration_crypto import encrypt_integration_secret
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
INTEGRATION_ID = "22222222-2222-2222-2222-222222222222"
WEBHOOK_URL = "https://hooks.slack.com/services/T000/B000/secret"


def test_integrations_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/integrations", params={"org_id": ORG_ID})
    assert response.status_code == 401


def test_integrations_list_sanitizes_secret(monkeypatch) -> None:
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
            assert url == "https://example.supabase.co/rest/v1/integrations"
            assert params == {
                "select": "id,org_id,type,status,config,created_at,updated_at",
                "org_id": f"eq.{ORG_ID}",
                "order": "type.asc",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [
                    {
                        "id": INTEGRATION_ID,
                        "org_id": ORG_ID,
                        "type": "slack",
                        "status": "enabled",
                        "config": {"webhook_encrypted": "ciphertext"},
                        "created_at": "2026-02-09T00:00:00Z",
                        "updated_at": "2026-02-09T00:00:00Z",
                    }
                ]
            )

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in integrations list test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/integrations", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "integrations": [
            {
                "id": INTEGRATION_ID,
                "org_id": ORG_ID,
                "type": "slack",
                "status": "enabled",
                "has_secret": True,
                "created_at": "2026-02-09T00:00:00Z",
                "updated_at": "2026-02-09T00:00:00Z",
            }
        ]
    }


def test_connect_slack_encrypts_secret_before_rpc(monkeypatch) -> None:
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

        async def post(self, url: str, json: dict[str, object], headers: dict[str, str]) -> FakeResponse:
            assert url == "https://example.supabase.co/rest/v1/rpc/upsert_integration"
            assert json["p_org_id"] == ORG_ID
            assert json["p_type"] == "slack"
            assert json["p_status"] == "enabled"
            assert isinstance(json["p_config"], dict)
            webhook_encrypted = json["p_config"].get("webhook_encrypted")
            assert isinstance(webhook_encrypted, str)
            assert webhook_encrypted != WEBHOOK_URL
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(INTEGRATION_ID)

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in connect slack test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/integrations/slack",
            json={"org_id": ORG_ID, "webhook_url": WEBHOOK_URL, "status": "enabled"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_slack_test_endpoint_sends_webhook(monkeypatch) -> None:
    encrypted = encrypt_integration_secret(WEBHOOK_URL)

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
            assert url == "https://example.supabase.co/rest/v1/integrations"
            assert params == {
                "select": "id,org_id,type,status,config,created_at,updated_at",
                "org_id": f"eq.{ORG_ID}",
                "type": "eq.slack",
                "limit": "1",
            }
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"
            return FakeResponse(
                [
                    {
                        "id": INTEGRATION_ID,
                        "org_id": ORG_ID,
                        "type": "slack",
                        "status": "enabled",
                        "config": {"webhook_encrypted": encrypted},
                        "created_at": "2026-02-09T00:00:00Z",
                        "updated_at": "2026-02-09T00:00:00Z",
                    }
                ]
            )

        async def post(self, url: str, json: dict[str, str]) -> FakeResponse:
            assert url == WEBHOOK_URL
            assert "text" in json
            return FakeResponse({})

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post("/api/v1/integrations/slack/test", json={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
