from fastapi.testclient import TestClient

from app.main import app


def test_me_requires_token() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/me")
    assert response.status_code == 401
