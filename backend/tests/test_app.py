from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def _set_required_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@z/db")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "test-key")
    monkeypatch.setenv("ALLOWED_HOSTS", "http://localhost,https://example.com")


def test_health_check(monkeypatch):
    _set_required_env(monkeypatch)
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_env_loading(monkeypatch):
    _set_required_env(monkeypatch)

    settings = get_settings()
    assert settings.SECRET_KEY == "test-secret"
    assert settings.DATABASE_URL == "postgresql://x:y@z/db"
    assert settings.SUPABASE_API_KEY == "test-key"
    assert settings.ALLOWED_HOSTS == ["http://localhost", "https://example.com"]


def test_cors_allows_configured_origin(monkeypatch):
    _set_required_env(monkeypatch)
    client = TestClient(app)
    headers = {
        "Origin": "http://localhost",
        "Access-Control-Request-Method": "GET",
    }
    response = client.options("/health", headers=headers)
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "http://localhost"
