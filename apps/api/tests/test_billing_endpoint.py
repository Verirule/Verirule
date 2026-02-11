from fastapi.testclient import TestClient

from app.api.v1.endpoints import billing as billing_endpoint
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"


def test_billing_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/billing", params={"org_id": ORG_ID})
    assert response.status_code == 401


def test_billing_returns_default_free_when_missing(monkeypatch) -> None:
    async def fake_select_org_billing(access_token: str, org_id: str):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return None

    monkeypatch.setattr(billing_endpoint, "select_org_billing", fake_select_org_billing)
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get("/api/v1/billing", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "org_id": ORG_ID,
        "plan": "free",
        "subscription_status": "inactive",
        "current_period_end": None,
    }


def test_billing_returns_stored_plan(monkeypatch) -> None:
    async def fake_select_org_billing(access_token: str, org_id: str):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return {
            "org_id": ORG_ID,
            "plan": "business",
            "subscription_status": "active",
            "current_period_end": "2026-03-01T00:00:00Z",
        }

    monkeypatch.setattr(billing_endpoint, "select_org_billing", fake_select_org_billing)
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get("/api/v1/billing", params={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "org_id": ORG_ID,
        "plan": "business",
        "subscription_status": "active",
        "current_period_end": "2026-03-01T00:00:00Z",
    }
