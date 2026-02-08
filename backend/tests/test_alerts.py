from __future__ import annotations

import uuid

from app.alerts.service import generate_alert_for_violation


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self._filters = []
        self._op = None
        self._payload = None
        self._limit = None
        self._select_fields = None

    def select(self, fields):
        self._select_fields = fields
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def eq(self, field, value):
        self._filters.append((field, value))
        return self

    def limit(self, count):
        self._limit = count
        return self

    def execute(self):
        table = self.client.tables.setdefault(self.table_name, [])
        if self._op == "insert":
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            inserted = []
            for payload in payloads:
                row = dict(payload)
                row.setdefault("id", str(uuid.uuid4()))
                table.append(row)
                inserted.append(row)
            return FakeResponse(inserted)

        if self._op == "update":
            updated = []
            for row in table:
                if all(row.get(f) == v for f, v in self._filters):
                    row.update(self._payload)
                    updated.append(row)
            return FakeResponse(updated)

        rows = table
        for field, value in self._filters:
            rows = [r for r in rows if r.get(field) == value]
        if self._limit is not None:
            rows = rows[: self._limit]
        if self._select_fields and self._select_fields != "*":
            fields = [f.strip() for f in self._select_fields.split(",")]
            rows = [{k: r.get(k) for k in fields} for r in rows]
        return FakeResponse(rows)


class FakeClient:
    def __init__(self):
        self.tables = {}
        self.auth = self
        self.admin = self

    def table(self, name):
        return FakeQuery(self, name)

    def get_user_by_id(self, user_id):
        return {"user": {"email": "user@example.com"}}


def _settings(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x:y@z/db")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_API_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
    monkeypatch.setenv("ALLOWED_HOSTS", "http://localhost")
    monkeypatch.setenv("INGESTION_FEED_URL", "https://example.com/feed.xml")
    monkeypatch.setenv("EMAIL_PROVIDER", "")
    return Settings()


def test_alert_generation_and_dedup(monkeypatch):
    settings = _settings(monkeypatch)
    client = FakeClient()

    violation = {
        "id": "v1",
        "business_id": "b1",
        "regulation_id": "r1",
        "severity": "high",
        "message": "Violation",
    }

    alert = generate_alert_for_violation(
        settings,
        violation,
        business_name="Acme",
        regulation_title="Reg A",
        user_id="u1",
        client=client,
    )
    assert alert is not None
    assert len(client.tables["alerts"]) == 1

    alert2 = generate_alert_for_violation(
        settings,
        violation,
        business_name="Acme",
        regulation_title="Reg A",
        user_id="u1",
        client=client,
    )
    assert alert2 is None
    assert len(client.tables["alerts"]) == 1
