from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints import members as members_endpoint
from app.auth.roles import OrgRoleContext
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"


def test_create_invite_requires_admin(monkeypatch) -> None:
    async def fake_enforce(*args, **kwargs):
        raise HTTPException(status_code=403, detail="Forbidden")

    async def fail_rpc(*args, **kwargs):
        raise AssertionError("create_org_invite RPC should not run when role guard fails")

    monkeypatch.setattr(members_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(members_endpoint, "rpc_create_org_invite", fail_rpc)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "11111111-1111-1111-1111-111111111112"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/orgs/{ORG_ID}/invites",
            json={"email": "teammate@example.com", "role": "member", "expires_hours": 72},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_accept_invite_returns_org_id_and_records_audit(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_accept(access_token: str, payload: dict[str, object]) -> str:
        assert access_token == "token-123"
        captured["accept_payload"] = payload
        return ORG_ID

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "token-123"
        captured["audit_payload"] = payload

    monkeypatch.setattr(members_endpoint, "rpc_accept_org_invite", fake_accept)
    monkeypatch.setattr(members_endpoint, "rpc_record_audit_event", fake_audit)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "11111111-1111-1111-1111-111111111113"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/invites/accept",
            json={"token": "invite-token-123"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"org_id": ORG_ID}
    assert captured["accept_payload"] == {"p_token": "invite-token-123"}

    audit_payload = captured["audit_payload"]
    assert isinstance(audit_payload, dict)
    assert audit_payload["p_org_id"] == ORG_ID
    assert audit_payload["p_action"] == "org_invite_accepted"


def test_create_invite_returns_402_when_member_limit_reached(monkeypatch) -> None:
    async def fake_enforce(auth, org_id: str, min_role: str) -> OrgRoleContext:
        assert org_id == ORG_ID
        assert min_role == "admin"
        return OrgRoleContext(org_id=org_id, user_id="11111111-1111-1111-1111-111111111112", role="admin")

    async def fake_select_org_billing(access_token: str, org_id: str) -> dict[str, str]:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return {"id": org_id, "plan": "free"}

    async def fake_select_org_members_service(org_id: str) -> list[dict[str, str]]:
        assert org_id == ORG_ID
        return [
            {"org_id": org_id, "user_id": "u1", "role": "owner"},
            {"org_id": org_id, "user_id": "u2", "role": "admin"},
            {"org_id": org_id, "user_id": "u3", "role": "member"},
        ]

    async def fake_select_org_invites(access_token: str, org_id: str, *, pending_only: bool = False):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert pending_only is True
        return [
            {"id": "inv-1", "email": "a@example.com"},
            {"id": "inv-2", "email": "b@example.com"},
        ]

    async def fail_create_invite(*args, **kwargs):  # pragma: no cover
        raise AssertionError("create_org_invite RPC should not run when member limit is reached")

    monkeypatch.setattr(members_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(members_endpoint, "select_org_billing", fake_select_org_billing)
    monkeypatch.setattr(members_endpoint, "select_org_members_service", fake_select_org_members_service)
    monkeypatch.setattr(members_endpoint, "select_org_invites", fake_select_org_invites)
    monkeypatch.setattr(members_endpoint, "rpc_create_org_invite", fail_create_invite)

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "11111111-1111-1111-1111-111111111112"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/orgs/{ORG_ID}/invites",
            json={"email": "teammate@example.com", "role": "member", "expires_hours": 72},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 402
    assert response.json() == {"detail": "Member limit reached (5). Upgrade required."}
