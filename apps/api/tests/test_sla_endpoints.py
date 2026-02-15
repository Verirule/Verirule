from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints import sla as sla_endpoint
from app.auth.roles import OrgRoleContext
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "11111111-1111-1111-1111-111111111112"


def _auth() -> VerifiedSupabaseAuth:
    return VerifiedSupabaseAuth(access_token="token-123", claims={"sub": USER_ID})


def test_get_org_sla_enforces_admin_role(monkeypatch) -> None:
    async def fake_enforce(*args, **kwargs):
        raise HTTPException(status_code=403, detail="Forbidden")

    async def fail_ensure(*args, **kwargs):  # pragma: no cover
        raise AssertionError("ensure_org_sla_rules should not run when role guard fails")

    monkeypatch.setattr(sla_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(sla_endpoint, "ensure_org_sla_rules", fail_ensure)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/sla")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_get_org_sla_returns_defaults(monkeypatch) -> None:
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
            "due_hours_low": 168,
            "due_hours_medium": 72,
            "due_hours_high": 24,
            "due_soon_threshold_hours": 12,
            "overdue_remind_every_hours": 24,
            "created_at": "2026-02-14T00:00:00Z",
            "updated_at": "2026-02-14T00:00:00Z",
        }

    monkeypatch.setattr(sla_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(sla_endpoint, "ensure_org_sla_rules", fake_ensure)
    monkeypatch.setattr(sla_endpoint, "get_org_sla_rules", fake_get)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/sla")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "org_id": ORG_ID,
        "enabled": True,
        "due_hours_low": 168,
        "due_hours_medium": 72,
        "due_hours_high": 24,
        "due_soon_threshold_hours": 12,
        "overdue_remind_every_hours": 24,
        "created_at": "2026-02-14T00:00:00Z",
        "updated_at": "2026-02-14T00:00:00Z",
    }


def test_put_org_sla_updates_and_records_audit(monkeypatch) -> None:
    audit_payloads: list[dict[str, object]] = []

    async def fake_enforce(auth, org_id: str, min_role: str) -> OrgRoleContext:
        assert min_role == "admin"
        return OrgRoleContext(org_id=org_id, user_id=USER_ID, role="admin")

    async def fake_ensure(access_token: str, org_id: str) -> None:
        assert access_token == "token-123"
        assert org_id == ORG_ID

    async def fake_get(access_token: str, org_id: str):
        return {
            "org_id": ORG_ID,
            "enabled": True,
            "due_hours_low": 168,
            "due_hours_medium": 72,
            "due_hours_high": 24,
            "due_soon_threshold_hours": 12,
            "overdue_remind_every_hours": 24,
            "created_at": "2026-02-14T00:00:00Z",
            "updated_at": "2026-02-14T00:00:00Z",
        }

    async def fake_update(access_token: str, org_id: str, patch: dict[str, object]):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert patch == {"enabled": False, "due_hours_high": 12, "overdue_remind_every_hours": 6}
        return {
            "org_id": ORG_ID,
            "enabled": False,
            "due_hours_low": 168,
            "due_hours_medium": 72,
            "due_hours_high": 12,
            "due_soon_threshold_hours": 12,
            "overdue_remind_every_hours": 6,
            "created_at": "2026-02-14T00:00:00Z",
            "updated_at": "2026-02-14T01:00:00Z",
        }

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "token-123"
        audit_payloads.append(payload)

    monkeypatch.setattr(sla_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(sla_endpoint, "ensure_org_sla_rules", fake_ensure)
    monkeypatch.setattr(sla_endpoint, "get_org_sla_rules", fake_get)
    monkeypatch.setattr(sla_endpoint, "update_org_sla_rules", fake_update)
    monkeypatch.setattr(sla_endpoint, "rpc_record_audit_event", fake_audit)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.put(
            f"/api/v1/orgs/{ORG_ID}/sla",
            json={"enabled": False, "due_hours_high": 12, "overdue_remind_every_hours": 6},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["due_hours_high"] == 12
    assert response.json()["overdue_remind_every_hours"] == 6
    assert len(audit_payloads) == 1
    assert audit_payloads[0]["p_action"] == "org_sla_rules_updated"
