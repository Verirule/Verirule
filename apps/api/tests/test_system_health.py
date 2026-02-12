from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.v1.endpoints import system as system_endpoint
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app


def _settings(stale_after_seconds: int = 180):
    return type("Settings", (), {"WORKER_STALE_AFTER_SECONDS": stale_after_seconds})()


def test_system_health_unknown_without_worker_row(monkeypatch) -> None:
    async def fake_select_system_status(access_token: str):
        assert access_token == "token-123"
        return []

    monkeypatch.setattr(system_endpoint, "select_system_status", fake_select_system_status)
    monkeypatch.setattr(system_endpoint, "get_settings", lambda: _settings())
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": "user-1"}
    )

    try:
        client = TestClient(app)
        response = client.get("/api/v1/system/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "api": "ok",
        "worker": "unknown",
        "worker_last_seen_at": None,
        "stale_after_seconds": 180,
    }


def test_system_health_stale_with_old_worker_heartbeat(monkeypatch) -> None:
    old_time = (datetime.now(UTC) - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")

    async def fake_select_system_status(access_token: str):
        assert access_token == "token-123"
        return [{"id": "worker", "updated_at": old_time, "payload": {}}]

    monkeypatch.setattr(system_endpoint, "select_system_status", fake_select_system_status)
    monkeypatch.setattr(system_endpoint, "get_settings", lambda: _settings(stale_after_seconds=180))
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": "user-1"}
    )

    try:
        client = TestClient(app)
        response = client.get("/api/v1/system/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "ok"
    assert body["worker"] == "stale"
    assert body["worker_last_seen_at"] is not None
    assert body["stale_after_seconds"] == 180


def test_system_health_ok_with_recent_worker_heartbeat(monkeypatch) -> None:
    recent = (datetime.now(UTC) - timedelta(seconds=30)).isoformat().replace("+00:00", "Z")

    async def fake_select_system_status(access_token: str):
        assert access_token == "token-123"
        return [{"id": "worker", "updated_at": recent, "payload": {}}]

    monkeypatch.setattr(system_endpoint, "select_system_status", fake_select_system_status)
    monkeypatch.setattr(system_endpoint, "get_settings", lambda: _settings(stale_after_seconds=180))
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123", claims={"sub": "user-1"}
    )

    try:
        client = TestClient(app)
        response = client.get("/api/v1/system/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["api"] == "ok"
    assert body["worker"] == "ok"
    assert body["worker_last_seen_at"] is not None
    assert body["stale_after_seconds"] == 180
