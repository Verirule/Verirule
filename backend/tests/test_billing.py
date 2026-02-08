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
        self._op = None
        self._payload = None

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
        self._op = "update"
        self._payload = payload
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
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
        if self._op == "update":
            updated = []
            for row in rows:
                row.update(self._payload)
                updated.append(row)
            rows = updated
        if self._op == "insert":
            rows = [self._payload]
            self.rows.append(self._payload)
        if self._select and self._select != "*":
            fields = [f.strip() for f in self._select.split(",")]
            rows = [{k: r.get(k) for k in fields} for r in rows]
        return FakeResponse(rows)


class FakeClient:
    def __init__(self, rows_map):
        self.rows_map = rows_map

    def table(self, name):
        return FakeQuery(name, self.rows_map.setdefault(name, []))


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


def test_subscription_upgrade_and_isolation(monkeypatch):
    _set_env(monkeypatch)
    rows = {"subscriptions": []}
    fake_client = FakeClient(rows)
    monkeypatch.setattr("app.main.get_service_client", lambda settings: fake_client)

    token = _token("user", user_id="user-1")
    client = TestClient(app)
    response = client.post(
        "/subscription/upgrade", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert rows["subscriptions"][0]["user_id"] == "user-1"
    assert rows["subscriptions"][0]["plan"] == "pro"


def test_business_limit_free_plan(monkeypatch):
    _set_env(monkeypatch)
    rows = {
        "subscriptions": [{"id": "s1", "user_id": "user-1", "plan": "free", "status": "active"}],
        "business_profiles": [
            {"id": "b1", "user_id": "user-1", "business_name": "A"}
        ],
    }
    fake_client = FakeClient(rows)
    monkeypatch.setattr("app.main.get_service_client", lambda settings: fake_client)

    token = _token("user", user_id="user-1")
    client = TestClient(app)
    response = client.post(
        "/business/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"business_name": "B", "industry": "fin", "jurisdiction": "us"},
    )
    assert response.status_code == 403


def test_business_create_pro_plan(monkeypatch):
    _set_env(monkeypatch)
    rows = {
        "subscriptions": [{"id": "s1", "user_id": "user-1", "plan": "pro", "status": "active"}],
        "business_profiles": [],
    }
    fake_client = FakeClient(rows)
    monkeypatch.setattr("app.main.get_service_client", lambda settings: fake_client)

    token = _token("user", user_id="user-1")
    client = TestClient(app)
    response = client.post(
        "/business/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"business_name": "B", "industry": "fin", "jurisdiction": "us"},
    )
    assert response.status_code == 200


def test_ingestion_limit_free_plan(monkeypatch):
    _set_env(monkeypatch)
    rows = {
        "subscriptions": [{"id": "s1", "user_id": "user-1", "plan": "free", "status": "active"}],
        "regulation_versions": [
            {"id": "v1", "detected_at": "2030-01-01T00:00:00+00:00"}
        ],
    }
    fake_client = FakeClient(rows)
    monkeypatch.setattr("app.main.get_service_client", lambda settings: fake_client)

    token = _token("admin", user_id="user-1")
    client = TestClient(app)
    response = client.post("/ingest/run", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 429
