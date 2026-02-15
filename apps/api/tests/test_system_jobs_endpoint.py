from fastapi.testclient import TestClient

from app.api.v1.endpoints import system as system_endpoint
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app


def _set_auth_override() -> None:
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )


def test_system_jobs_requires_admin_or_owner(monkeypatch) -> None:
    async def fake_select_org_ids_for_roles(access_token: str, user_id: str, *, roles: tuple[str, ...]):
        assert access_token == "token-123"
        assert user_id == "user-1"
        assert roles == ("owner", "admin")
        return []

    monkeypatch.setattr(system_endpoint, "select_org_ids_for_roles", fake_select_org_ids_for_roles)
    _set_auth_override()

    try:
        client = TestClient(app)
        response = client.get("/api/v1/system/jobs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_system_jobs_returns_safe_failed_rows(monkeypatch) -> None:
    async def fake_select_org_ids_for_roles(access_token: str, user_id: str, *, roles: tuple[str, ...]):
        return ["org-1"]

    async def fake_failed_notifications(*, org_ids: list[str], limit: int):
        assert org_ids == ["org-1"]
        assert limit == 50
        return [
            {
                "id": "notif-1",
                "org_id": "org-1",
                "type": "digest",
                "status": "failed",
                "attempts": 3,
                "last_error": "smtp timeout",
                "updated_at": "2026-02-15T01:00:00Z",
                "payload": {"sensitive": True},
            }
        ]

    async def fake_failed_exports(*, org_ids: list[str], limit: int):
        return [
            {
                "id": "export-1",
                "org_id": "org-1",
                "status": "failed",
                "attempts": 2,
                "last_error": "zip failed",
                "created_at": "2026-02-14T23:00:00Z",
                "completed_at": "2026-02-15T00:00:00Z",
            }
        ]

    async def fake_failed_monitoring(*, org_ids: list[str], limit: int):
        return [
            {
                "id": "run-1",
                "org_id": "org-1",
                "status": "failed",
                "attempts": 5,
                "last_error": "fetch failed",
                "finished_at": "2026-02-14T22:00:00Z",
                "created_at": "2026-02-14T21:00:00Z",
            }
        ]

    monkeypatch.setattr(system_endpoint, "select_org_ids_for_roles", fake_select_org_ids_for_roles)
    monkeypatch.setattr(
        system_endpoint, "select_failed_notification_jobs_service", fake_failed_notifications
    )
    monkeypatch.setattr(system_endpoint, "select_failed_audit_exports_service", fake_failed_exports)
    monkeypatch.setattr(system_endpoint, "select_failed_monitor_runs_service", fake_failed_monitoring)
    _set_auth_override()

    try:
        client = TestClient(app)
        response = client.get("/api/v1/system/jobs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["jobs"]) == 3
    assert all(
        set(job.keys())
        == {"id", "org_id", "type", "status", "attempts", "last_error", "updated_at"}
        for job in body["jobs"]
    )
    assert body["jobs"][0]["id"] == "notif-1"
    assert body["jobs"][1]["id"] == "export-1"
    assert body["jobs"][2]["id"] == "run-1"


def test_system_jobs_type_filter_notifications_only(monkeypatch) -> None:
    async def fake_select_org_ids_for_roles(access_token: str, user_id: str, *, roles: tuple[str, ...]):
        return ["org-1"]

    async def fake_failed_notifications(*, org_ids: list[str], limit: int):
        return [
            {
                "id": "notif-1",
                "org_id": "org-1",
                "type": "sla",
                "status": "failed",
                "attempts": 1,
                "last_error": None,
                "updated_at": "2026-02-15T01:00:00Z",
            }
        ]

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("unexpected call")

    monkeypatch.setattr(system_endpoint, "select_org_ids_for_roles", fake_select_org_ids_for_roles)
    monkeypatch.setattr(
        system_endpoint, "select_failed_notification_jobs_service", fake_failed_notifications
    )
    monkeypatch.setattr(system_endpoint, "select_failed_audit_exports_service", fail_if_called)
    monkeypatch.setattr(system_endpoint, "select_failed_monitor_runs_service", fail_if_called)
    _set_auth_override()

    try:
        client = TestClient(app)
        response = client.get("/api/v1/system/jobs?type=notifications")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "jobs": [
            {
                "id": "notif-1",
                "org_id": "org-1",
                "type": "sla",
                "status": "failed",
                "attempts": 1,
                "last_error": None,
                "updated_at": "2026-02-15T01:00:00Z",
            }
        ]
    }
