from fastapi.testclient import TestClient

from app.api.v1.endpoints import automation as automation_endpoint
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"


def test_get_alert_task_rules_returns_defaults(monkeypatch) -> None:
    async def fake_ensure(access_token: str, org_id: str) -> None:
        assert access_token == "token-123"
        assert org_id == ORG_ID

    async def fake_get_rules(access_token: str, org_id: str):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return {
            "org_id": ORG_ID,
            "enabled": True,
            "auto_create_task_on_alert": True,
            "min_severity": "medium",
            "auto_link_suggested_controls": True,
            "auto_add_evidence_checklist": True,
            "created_at": "2026-02-13T00:00:00Z",
            "updated_at": "2026-02-13T00:00:00Z",
        }

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(automation_endpoint, "ensure_alert_task_rules", fake_ensure)
    monkeypatch.setattr(automation_endpoint, "get_alert_task_rules", fake_get_rules)

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/automation/alert-task-rules")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "org_id": ORG_ID,
        "enabled": True,
        "auto_create_task_on_alert": True,
        "min_severity": "medium",
        "auto_link_suggested_controls": True,
        "auto_add_evidence_checklist": True,
        "created_at": "2026-02-13T00:00:00Z",
        "updated_at": "2026-02-13T00:00:00Z",
    }


def test_put_alert_task_rules_updates_patch(monkeypatch) -> None:
    updates: list[dict[str, object]] = []

    async def fake_ensure(access_token: str, org_id: str) -> None:
        assert access_token == "token-123"
        assert org_id == ORG_ID

    async def fake_update(access_token: str, org_id: str, patch: dict[str, object]):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        updates.append(patch)
        return {
            "org_id": ORG_ID,
            "enabled": True,
            "auto_create_task_on_alert": False,
            "min_severity": "high",
            "auto_link_suggested_controls": False,
            "auto_add_evidence_checklist": True,
            "created_at": "2026-02-13T00:00:00Z",
            "updated_at": "2026-02-13T01:00:00Z",
        }

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(automation_endpoint, "ensure_alert_task_rules", fake_ensure)
    monkeypatch.setattr(automation_endpoint, "update_alert_task_rules", fake_update)

    try:
        client = TestClient(app)
        response = client.put(
            f"/api/v1/orgs/{ORG_ID}/automation/alert-task-rules",
            json={
                "auto_create_task_on_alert": False,
                "min_severity": "high",
                "auto_link_suggested_controls": False,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert updates == [
        {
            "auto_create_task_on_alert": False,
            "min_severity": "high",
            "auto_link_suggested_controls": False,
        }
    ]
    assert response.json()["min_severity"] == "high"
    assert response.json()["auto_create_task_on_alert"] is False
