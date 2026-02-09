import os

from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
