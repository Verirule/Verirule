from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints import notifications as notifications_endpoint
from app.auth.roles import OrgRoleContext
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "11111111-1111-1111-1111-111111111112"


def _auth() -> VerifiedSupabaseAuth:
    return VerifiedSupabaseAuth(access_token="token-123", claims={"sub": USER_ID})


def test_get_org_notification_rules_enforces_admin_role(monkeypatch) -> None:
    async def fake_enforce(*args, **kwargs):
        raise HTTPException(status_code=403, detail="Forbidden")

    async def fail_ensure(*args, **kwargs):  # pragma: no cover
        raise AssertionError("ensure_org_notification_rules should not run when role guard fails")

    monkeypatch.setattr(notifications_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(notifications_endpoint, "ensure_org_notification_rules", fail_ensure)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/notifications/rules")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_get_org_notification_rules_returns_defaults(monkeypatch) -> None:
    async def fake_enforce(auth, org_id: str, min_role: str) -> OrgRoleContext:
        assert org_id == ORG_ID
        assert min_role == "admin"
        return OrgRoleContext(org_id=org_id, user_id=USER_ID, role="admin")

    async def fake_ensure(access_token: str, org_id: str) -> None:
        assert access_token == "token-123"
        assert org_id == ORG_ID

    async def fake_get(access_token: str, org_id: str):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return {
            "org_id": ORG_ID,
            "enabled": True,
            "mode": "digest",
            "digest_cadence": "daily",
            "min_severity": "medium",
            "last_digest_sent_at": None,
            "created_at": "2026-02-14T00:00:00Z",
            "updated_at": "2026-02-14T00:00:00Z",
        }

    monkeypatch.setattr(notifications_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(notifications_endpoint, "ensure_org_notification_rules", fake_ensure)
    monkeypatch.setattr(notifications_endpoint, "get_org_notification_rules", fake_get)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/notifications/rules")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "org_id": ORG_ID,
        "enabled": True,
        "mode": "digest",
        "digest_cadence": "daily",
        "min_severity": "medium",
        "last_digest_sent_at": None,
        "created_at": "2026-02-14T00:00:00Z",
        "updated_at": "2026-02-14T00:00:00Z",
    }


def test_put_org_notification_rules_records_audit(monkeypatch) -> None:
    audit_payloads: list[dict[str, object]] = []

    async def fake_enforce(auth, org_id: str, min_role: str) -> OrgRoleContext:
        assert min_role == "admin"
        return OrgRoleContext(org_id=org_id, user_id=USER_ID, role="admin")

    async def fake_ensure(access_token: str, org_id: str) -> None:
        assert access_token == "token-123"
        assert org_id == ORG_ID

    async def fake_update(access_token: str, org_id: str, patch: dict[str, object]):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert patch == {"enabled": False, "min_severity": "high"}
        return {
            "org_id": ORG_ID,
            "enabled": False,
            "mode": "digest",
            "digest_cadence": "daily",
            "min_severity": "high",
            "last_digest_sent_at": None,
            "created_at": "2026-02-14T00:00:00Z",
            "updated_at": "2026-02-14T01:00:00Z",
        }

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "token-123"
        audit_payloads.append(payload)

    monkeypatch.setattr(notifications_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(notifications_endpoint, "ensure_org_notification_rules", fake_ensure)
    monkeypatch.setattr(notifications_endpoint, "update_org_notification_rules", fake_update)
    monkeypatch.setattr(notifications_endpoint, "rpc_record_audit_event", fake_audit)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.put(
            f"/api/v1/orgs/{ORG_ID}/notifications/rules",
            json={"enabled": False, "min_severity": "high"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["min_severity"] == "high"
    assert len(audit_payloads) == 1
    assert audit_payloads[0]["p_action"] == "org_notification_rules_updated"


def test_me_notifications_get_and_put(monkeypatch) -> None:
    async def fake_ensure(access_token: str) -> None:
        assert access_token == "token-123"

    async def fake_get(access_token: str):
        assert access_token == "token-123"
        return {
            "user_id": USER_ID,
            "email_enabled": True,
            "created_at": "2026-02-14T00:00:00Z",
            "updated_at": "2026-02-14T00:00:00Z",
        }

    async def fake_update(access_token: str, patch: dict[str, object]):
        assert access_token == "token-123"
        assert patch == {"email_enabled": False}
        return {
            "user_id": USER_ID,
            "email_enabled": False,
            "created_at": "2026-02-14T00:00:00Z",
            "updated_at": "2026-02-14T01:00:00Z",
        }

    monkeypatch.setattr(notifications_endpoint, "ensure_user_notification_prefs", fake_ensure)
    monkeypatch.setattr(notifications_endpoint, "get_user_notification_prefs", fake_get)
    monkeypatch.setattr(notifications_endpoint, "update_user_notification_prefs", fake_update)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        get_response = client.get("/api/v1/me/notifications")
        put_response = client.put("/api/v1/me/notifications", json={"email_enabled": False})
    finally:
        app.dependency_overrides.clear()

    assert get_response.status_code == 200
    assert get_response.json() == {
        "user_id": USER_ID,
        "email_enabled": True,
        "created_at": "2026-02-14T00:00:00Z",
        "updated_at": "2026-02-14T00:00:00Z",
    }
    assert put_response.status_code == 200
    assert put_response.json() == {
        "user_id": USER_ID,
        "email_enabled": False,
        "created_at": "2026-02-14T00:00:00Z",
        "updated_at": "2026-02-14T01:00:00Z",
    }

