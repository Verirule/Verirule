from fastapi.testclient import TestClient

from app.api.v1.endpoints import system as system_endpoint
from app.main import app


def _settings():
    return type(
        "Settings",
        (),
        {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_ANON_KEY": "anon-key",
            "APP_VERSION": "2026.02.15",
        },
    )()


def test_system_health_public_and_ok(monkeypatch) -> None:
    async def fake_probe_supabase_health(*, supabase_url: str, supabase_anon_key: str) -> bool:
        assert supabase_url == "https://example.supabase.co"
        assert supabase_anon_key == "anon-key"
        return True

    monkeypatch.setattr(system_endpoint, "_probe_supabase_health", fake_probe_supabase_health)
    monkeypatch.setattr(system_endpoint, "get_settings", _settings)

    client = TestClient(app)
    response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["version"] == "2026.02.15"
    assert isinstance(body["time_utc"], str)
    assert body["time_utc"].endswith("Z")
    assert body["supabase_ok"] is True


def test_system_health_returns_200_when_supabase_probe_fails(monkeypatch) -> None:
    async def fake_probe_supabase_health(*, supabase_url: str, supabase_anon_key: str) -> bool:
        return False

    monkeypatch.setattr(system_endpoint, "_probe_supabase_health", fake_probe_supabase_health)
    monkeypatch.setattr(system_endpoint, "get_settings", _settings)

    client = TestClient(app)
    response = client.get("/api/v1/system/health")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["version"] == "2026.02.15"
    assert body["supabase_ok"] is False
