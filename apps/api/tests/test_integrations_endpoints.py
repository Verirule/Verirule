import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import integrations as integrations_endpoint
from app.billing import guard as billing_guard
from app.core import crypto as crypto_core
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.integrations import jira as jira_integration
from app.integrations import slack as slack_integration
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
ALERT_ID = "22222222-2222-2222-2222-222222222222"
FINDING_ID = "33333333-3333-3333-3333-333333333333"
INTEGRATION_ID = "44444444-4444-4444-4444-444444444444"
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/T000/B000/secret"
JIRA_BASE_URL = "https://example.atlassian.net"
JIRA_EMAIL = "user@example.com"
JIRA_TOKEN = "jira-token"
JIRA_PROJECT = "VR"


async def fake_paid_plan(access_token: str, org_id: str) -> dict[str, str]:
    assert access_token == "token-123"
    assert org_id == ORG_ID
    return {"org_id": org_id, "plan": "pro"}


async def fake_free_plan(access_token: str, org_id: str) -> dict[str, str]:
    assert access_token == "token-123"
    assert org_id == ORG_ID
    return {"org_id": org_id, "plan": "free"}


@pytest.fixture(autouse=True)
def _default_paid_plan(monkeypatch) -> None:
    monkeypatch.setattr(billing_guard, "select_org_billing", fake_paid_plan)


def test_integrations_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/integrations", params={"org_id": ORG_ID})
    assert response.status_code == 401


def test_connect_slack_stores_ciphertext(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_upsert(access_token: str, payload: dict[str, object]) -> str:
        assert access_token == "token-123"
        captured.update(payload)
        return INTEGRATION_ID

    monkeypatch.setattr(integrations_endpoint, "rpc_upsert_integration", fake_upsert)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/integrations/slack/connect",
            json={"org_id": ORG_ID, "webhook_url": SLACK_WEBHOOK_URL},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert captured["p_org_id"] == ORG_ID
    assert captured["p_type"] == "slack"
    assert captured["p_status"] == "connected"
    assert captured["p_config"] == {"channel_hint": ""}
    assert isinstance(captured["p_secret_ciphertext"], str)
    assert captured["p_secret_ciphertext"] != SLACK_WEBHOOK_URL


def test_connect_slack_returns_501_when_secrets_key_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        crypto_core,
        "get_settings",
        lambda: type("Settings", (), {"VERIRULE_SECRETS_KEY": None})(),
    )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/integrations/slack/connect",
            json={"org_id": ORG_ID, "webhook_url": SLACK_WEBHOOK_URL},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 501
    assert response.json() == {"detail": "Integration secrets are not configured."}


def test_slack_test_endpoint_returns_200(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, str]) -> FakeResponse:
            assert url == SLACK_WEBHOOK_URL
            assert isinstance(json.get("text"), str)
            return FakeResponse()

    ciphertext = crypto_core.encrypt_json({"webhook_url": SLACK_WEBHOOK_URL})

    async def fake_select_secret(access_token: str, org_id: str, integration_type: str) -> dict[str, object]:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert integration_type == "slack"
        return {
            "id": INTEGRATION_ID,
            "org_id": ORG_ID,
            "type": "slack",
            "status": "connected",
            "config": {"channel_hint": ""},
            "secret_ciphertext": ciphertext,
            "updated_at": "2026-02-10T00:00:00Z",
        }

    monkeypatch.setattr(integrations_endpoint, "select_integration_secret", fake_select_secret)
    monkeypatch.setattr(slack_integration.httpx, "AsyncClient", FakeAsyncClient)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post("/api/v1/integrations/slack/test", json={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_jira_test_endpoint_returns_200(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"accountId": "abc"}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, headers: dict[str, str]) -> FakeResponse:
            assert url == f"{JIRA_BASE_URL}/rest/api/3/myself"
            assert headers.get("Authorization", "").startswith("Basic ")
            return FakeResponse()

    ciphertext = crypto_core.encrypt_json(
        {
            "base_url": JIRA_BASE_URL,
            "email": JIRA_EMAIL,
            "api_token": JIRA_TOKEN,
            "project_key": JIRA_PROJECT,
        }
    )

    async def fake_select_secret(access_token: str, org_id: str, integration_type: str) -> dict[str, object]:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert integration_type == "jira"
        return {
            "id": INTEGRATION_ID,
            "org_id": ORG_ID,
            "type": "jira",
            "status": "connected",
            "config": {"base_url": JIRA_BASE_URL, "project_key": JIRA_PROJECT},
            "secret_ciphertext": ciphertext,
            "updated_at": "2026-02-10T00:00:00Z",
        }

    monkeypatch.setattr(integrations_endpoint, "select_integration_secret", fake_select_secret)
    monkeypatch.setattr(jira_integration.httpx, "AsyncClient", FakeAsyncClient)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post("/api/v1/integrations/jira/test", json={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_slack_notify_returns_200(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, str]) -> FakeResponse:
            assert url == SLACK_WEBHOOK_URL
            assert "Verirule alert" in json.get("text", "")
            return FakeResponse()

    ciphertext = crypto_core.encrypt_json({"webhook_url": SLACK_WEBHOOK_URL})

    async def fake_select_secret(access_token: str, org_id: str, integration_type: str) -> dict[str, object]:
        return {
            "id": INTEGRATION_ID,
            "org_id": ORG_ID,
            "type": "slack",
            "status": "connected",
            "config": {"channel_hint": ""},
            "secret_ciphertext": ciphertext,
            "updated_at": "2026-02-10T00:00:00Z",
        }

    async def fake_select_alert_by_id(access_token: str, alert_id: str) -> dict[str, object]:
        assert alert_id == ALERT_ID
        return {
            "id": ALERT_ID,
            "org_id": ORG_ID,
            "finding_id": FINDING_ID,
            "status": "open",
            "owner_user_id": None,
            "created_at": "2026-02-10T00:00:00Z",
            "resolved_at": None,
        }

    async def fake_select_finding_by_id(access_token: str, finding_id: str) -> dict[str, object]:
        assert finding_id == FINDING_ID
        return {
            "id": FINDING_ID,
            "org_id": ORG_ID,
            "source_id": "55555555-5555-5555-5555-555555555555",
            "run_id": "66666666-6666-6666-6666-666666666666",
            "title": "TLS cert changed",
            "summary": "Unexpected cert change detected.",
            "severity": "high",
            "detected_at": "2026-02-10T00:00:00Z",
            "fingerprint": "fp",
            "raw_url": None,
            "raw_hash": None,
        }

    monkeypatch.setattr(integrations_endpoint, "select_integration_secret", fake_select_secret)
    monkeypatch.setattr(integrations_endpoint, "select_alert_by_id", fake_select_alert_by_id)
    monkeypatch.setattr(integrations_endpoint, "select_finding_by_id", fake_select_finding_by_id)
    monkeypatch.setattr(slack_integration.httpx, "AsyncClient", FakeAsyncClient)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/integrations/slack/notify",
            json={"org_id": ORG_ID, "alert_id": ALERT_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_jira_create_issue_returns_issue_data(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload: dict[str, str]) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self.payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            assert url == f"{JIRA_BASE_URL}/rest/api/3/issue"
            assert headers.get("Authorization", "").startswith("Basic ")
            assert isinstance(json["fields"], dict)
            return FakeResponse({"key": "VR-123"})

    ciphertext = crypto_core.encrypt_json(
        {
            "base_url": JIRA_BASE_URL,
            "email": JIRA_EMAIL,
            "api_token": JIRA_TOKEN,
            "project_key": JIRA_PROJECT,
        }
    )

    async def fake_select_secret(access_token: str, org_id: str, integration_type: str) -> dict[str, object]:
        return {
            "id": INTEGRATION_ID,
            "org_id": ORG_ID,
            "type": "jira",
            "status": "connected",
            "config": {"base_url": JIRA_BASE_URL, "project_key": JIRA_PROJECT},
            "secret_ciphertext": ciphertext,
            "updated_at": "2026-02-10T00:00:00Z",
        }

    async def fake_select_alert_by_id(access_token: str, alert_id: str) -> dict[str, object]:
        assert alert_id == ALERT_ID
        return {
            "id": ALERT_ID,
            "org_id": ORG_ID,
            "finding_id": FINDING_ID,
            "status": "open",
            "owner_user_id": None,
            "created_at": "2026-02-10T00:00:00Z",
            "resolved_at": None,
        }

    async def fake_select_finding_by_id(access_token: str, finding_id: str) -> dict[str, object]:
        assert finding_id == FINDING_ID
        return {
            "id": FINDING_ID,
            "org_id": ORG_ID,
            "source_id": "55555555-5555-5555-5555-555555555555",
            "run_id": "66666666-6666-6666-6666-666666666666",
            "title": "TLS cert changed",
            "summary": "Unexpected cert change detected.",
            "severity": "high",
            "detected_at": "2026-02-10T00:00:00Z",
            "fingerprint": "fp",
            "raw_url": None,
            "raw_hash": None,
        }

    monkeypatch.setattr(integrations_endpoint, "select_integration_secret", fake_select_secret)
    monkeypatch.setattr(integrations_endpoint, "select_alert_by_id", fake_select_alert_by_id)
    monkeypatch.setattr(integrations_endpoint, "select_finding_by_id", fake_select_finding_by_id)
    monkeypatch.setattr(jira_integration.httpx, "AsyncClient", FakeAsyncClient)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/integrations/jira/create-issue",
            json={"org_id": ORG_ID, "alert_id": ALERT_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"issueKey": "VR-123", "url": f"{JIRA_BASE_URL}/browse/VR-123"}


def test_connect_slack_returns_402_on_free_plan(monkeypatch) -> None:
    monkeypatch.setattr(billing_guard, "select_org_billing", fake_free_plan)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/integrations/slack/connect",
            json={"org_id": ORG_ID, "webhook_url": SLACK_WEBHOOK_URL},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 402
    assert response.json() == {"detail": "Upgrade required"}


def test_slack_notify_returns_402_on_free_plan(monkeypatch) -> None:
    monkeypatch.setattr(billing_guard, "select_org_billing", fake_free_plan)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/integrations/slack/notify",
            json={"org_id": ORG_ID, "alert_id": ALERT_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 402
    assert response.json() == {"detail": "Upgrade required"}
