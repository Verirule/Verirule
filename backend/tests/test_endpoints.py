import jwt
from fastapi.testclient import TestClient

from app.main import app


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, table, rows):
        self.table = table
        self.rows = rows
        self._filters = []
        self._select = None
        self._order_field = None
        self._desc = False
        self._limit = None
        self._range = None
        self._update = None

    def select(self, fields):
        self._select = fields
        return self

    def eq(self, field, value):
        self._filters.append((field, value))
        return self

    def order(self, field, desc=False):
        self._order_field = field
        self._desc = desc
        return self

    def limit(self, count):
        self._limit = count
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def update(self, payload):
        self._update = payload
        return self

    def execute(self):
        rows = self.rows
        for field, value in self._filters:
            rows = [r for r in rows if r.get(field) == value]
        if self._order_field:
            rows = sorted(rows, key=lambda r: r.get(self._order_field), reverse=self._desc)
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        elif self._limit is not None:
            rows = rows[: self._limit]
        if self._update is not None:
            updated = []
            for row in rows:
                row.update(self._update)
                updated.append(row)
            rows = updated
        if self._select and self._select != "*":
            fields = [f.strip() for f in self._select.split(",")]
            rows = [{k: r.get(k) for k in fields} for r in rows]
        return FakeResponse(rows)


class FakeClient:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        return FakeQuery(name, self.rows)


def _set_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@z/db")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("ALLOWED_HOSTS", "http://localhost,https://example.com")
    monkeypatch.setenv("INGESTION_FEED_URL", "https://example.com/feed.xml")


def _token(role: str, user_id: str = "user-1"):
    payload = {"sub": user_id, "role": role}
    return jwt.encode(payload, "jwt-secret", algorithm="HS256")


def test_regulations_requires_auth(monkeypatch):
    _set_env(monkeypatch)
    client = TestClient(app)
    response = client.get("/regulations")
    assert response.status_code == 401


def test_regulations_list(monkeypatch):
    _set_env(monkeypatch)
    rows = [
        {
            "id": "r1",
            "title": "Rule A",
            "summary": "S",
            "source": "rss",
            "source_url": "https://example.com/a",
            "jurisdiction": "us",
            "industry": "finance",
            "published_at": None,
            "last_updated_at": "2024-01-01T00:00:00Z",
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]
    fake_client = FakeClient(rows)
    monkeypatch.setattr("app.main.get_supabase_service_client", lambda settings: fake_client)

    token = _token("user")
    client = TestClient(app)
    response = client.get(
        "/regulations?industry=finance&jurisdiction=us",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "r1"


def test_regulation_detail_excludes_raw_text(monkeypatch):
    _set_env(monkeypatch)
    rows = [
        {
            "id": "r1",
            "title": "Rule A",
            "summary": "S",
            "source": "rss",
            "source_url": "https://example.com/a",
            "jurisdiction": "us",
            "industry": "finance",
            "published_at": None,
            "last_updated_at": "2024-01-01T00:00:00Z",
            "created_at": "2024-01-01T00:00:00Z",
            "raw_text": "secret",
        }
    ]
    fake_client = FakeClient(rows)
    monkeypatch.setattr("app.main.get_supabase_service_client", lambda settings: fake_client)

    token = _token("user")
    client = TestClient(app)
    response = client.get("/regulations/r1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "raw_text" not in response.json()


def test_ingest_requires_admin(monkeypatch):
    _set_env(monkeypatch)
    token = _token("user")
    client = TestClient(app)
    response = client.post("/ingest/run", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_ingest_admin_success(monkeypatch):
    _set_env(monkeypatch)
    monkeypatch.setattr(
        "app.main.run_ingestion",
        lambda settings: {"fetched": 1, "inserted": 1, "updated": 0, "skipped": 0},
    )
    token = _token("admin")
    client = TestClient(app)
    response = client.post("/ingest/run", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["result"]["inserted"] == 1


def test_alerts_user_isolation(monkeypatch):
    _set_env(monkeypatch)
    rows = [
        {
            "id": "a1",
            "user_id": "user-1",
            "business_id": "b1",
            "violation_id": "v1",
            "severity": "high",
            "title": "Alert",
            "message": "Msg",
            "acknowledged": False,
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "a2",
            "user_id": "user-2",
            "business_id": "b2",
            "violation_id": "v2",
            "severity": "low",
            "title": "Alert",
            "message": "Msg",
            "acknowledged": False,
            "created_at": "2024-01-02T00:00:00Z",
        },
    ]
    fake_client = FakeClient(rows)
    monkeypatch.setattr("app.main.get_supabase_service_client", lambda settings: fake_client)

    token = _token("user", user_id="user-1")
    client = TestClient(app)
    response = client.get("/alerts", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["id"] == "a1"


def test_alert_acknowledge(monkeypatch):
    _set_env(monkeypatch)
    rows = [
        {
            "id": "a1",
            "user_id": "user-1",
            "business_id": "b1",
            "violation_id": "v1",
            "severity": "high",
            "title": "Alert",
            "message": "Msg",
            "acknowledged": False,
            "created_at": "2024-01-01T00:00:00Z",
        }
    ]
    fake_client = FakeClient(rows)
    monkeypatch.setattr("app.main.get_supabase_service_client", lambda settings: fake_client)

    token = _token("user", user_id="user-1")
    client = TestClient(app)
    response = client.post("/alerts/a1/acknowledge", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["acknowledged"] is True
