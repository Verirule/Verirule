import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints import billing as billing_endpoint
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def _default_owner_guard(monkeypatch) -> None:
    async def fake_enforce(*args, **kwargs) -> None:
        return None

    monkeypatch.setattr(billing_endpoint, "enforce_org_role", fake_enforce)


def test_billing_requires_token() -> None:
    client = TestClient(app)
    response = client.get(f"/api/v1/orgs/{ORG_ID}/billing")
    assert response.status_code == 401


def test_billing_events_requires_token() -> None:
    client = TestClient(app)
    response = client.get(f"/api/v1/orgs/{ORG_ID}/billing/events")
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
        response = client.get(f"/api/v1/orgs/{ORG_ID}/billing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["org_id"] == ORG_ID
    assert body["plan"] == "free"
    assert body["plan_status"] == "active"
    assert body["current_period_end"] is None
    assert body["entitlements"]["integrations_enabled"] is False
    assert body["entitlements"]["exports_enabled"] is False


def test_billing_returns_stored_plan(monkeypatch) -> None:
    async def fake_select_org_billing(access_token: str, org_id: str):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return {
            "id": ORG_ID,
            "plan": "business",
            "plan_status": "active",
            "stripe_customer_id": "cus_live_123",
            "stripe_subscription_id": "sub_live_123",
            "current_period_end": "2026-03-01T00:00:00Z",
        }

    monkeypatch.setattr(billing_endpoint, "select_org_billing", fake_select_org_billing)
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/billing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "org_id": ORG_ID,
        "plan": "business",
        "plan_status": "active",
        "stripe_customer_id": "cus_live_123",
        "stripe_subscription_id": "sub_live_123",
        "current_period_end": "2026-03-01T00:00:00Z",
        "entitlements": {
            "plan": "business",
            "integrations_enabled": True,
            "exports_enabled": True,
            "scheduling_enabled": True,
            "max_sources": None,
            "max_exports_per_month": None,
            "max_integrations": None,
        },
    }


def test_billing_events_returns_list(monkeypatch) -> None:
    async def fake_select_billing_events(access_token: str, org_id: str, *, limit: int):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert limit == 10
        return [
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "org_id": ORG_ID,
                "stripe_event_id": "evt_123",
                "event_type": "customer.subscription.updated",
                "created_at": "2026-02-13T00:00:00Z",
                "processed_at": "2026-02-13T00:00:01Z",
                "status": "processed",
                "error": None,
            }
        ]

    monkeypatch.setattr(billing_endpoint, "select_billing_events", fake_select_billing_events)
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/billing/events", params={"limit": 10})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "events": [
            {
                "id": "33333333-3333-3333-3333-333333333333",
                "org_id": ORG_ID,
                "stripe_event_id": "evt_123",
                "event_type": "customer.subscription.updated",
                "created_at": "2026-02-13T00:00:00Z",
                "processed_at": "2026-02-13T00:00:01Z",
                "status": "processed",
                "error": None,
            }
        ]
    }


def test_billing_routes_require_owner(monkeypatch) -> None:
    async def fake_enforce(*args, **kwargs) -> None:
        raise HTTPException(status_code=403, detail="Forbidden")

    async def fail_select(*args, **kwargs):
        raise AssertionError("billing query should not run when owner guard fails")

    monkeypatch.setattr(billing_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(billing_endpoint, "select_org_billing", fail_select)
    monkeypatch.setattr(billing_endpoint, "select_billing_events", fail_select)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        billing_response = client.get(f"/api/v1/orgs/{ORG_ID}/billing")
        events_response = client.get(f"/api/v1/orgs/{ORG_ID}/billing/events")
    finally:
        app.dependency_overrides.clear()

    assert billing_response.status_code == 403
    assert events_response.status_code == 403
