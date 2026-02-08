from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.ingestion.base import RegulationItem
from app.ingestion.service import upsert_regulations


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, client, table_name):
        self.client = client
        self.table_name = table_name
        self._filters = []
        self._select_fields = None
        self._order_field = None
        self._order_desc = False
        self._limit = None
        self._op = None
        self._payload = None

    def select(self, fields):
        self._op = "select"
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

    def order(self, field, desc=False):
        self._order_field = field
        self._order_desc = desc
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

        if self._order_field:
            rows = sorted(rows, key=lambda r: r.get(self._order_field), reverse=self._order_desc)
        if self._limit is not None:
            rows = rows[: self._limit]

        if self._select_fields and self._select_fields != "*":
            fields = [f.strip() for f in self._select_fields.split(",")]
            rows = [{k: r.get(k) for k in fields} for r in rows]

        return FakeResponse(rows)


class FakeClient:
    def __init__(self):
        self.tables = {}

    def table(self, name):
        return FakeQuery(self, name)


def _item(raw_text: str) -> RegulationItem:
    return RegulationItem(
        title="Rule A",
        summary="Summary",
        source="rss",
        source_url="https://example.com/rule-a",
        jurisdiction="",
        industry="",
        published_at=datetime.now(tz=timezone.utc),
        raw_text=raw_text,
    )


def test_ingestion_creates_and_versions():
    client = FakeClient()
    result = upsert_regulations(client, [_item("alpha")])
    assert result == {"created": 1, "updated": 0, "versioned": 1}
    assert len(client.tables["regulations"]) == 1
    assert len(client.tables["regulation_versions"]) == 1


def test_change_detection_creates_new_version():
    client = FakeClient()
    upsert_regulations(client, [_item("alpha")])
    result_same = upsert_regulations(client, [_item("alpha")])
    assert result_same == {"created": 0, "updated": 0, "versioned": 0}

    result_changed = upsert_regulations(client, [_item("bravo")])
    assert result_changed == {"created": 0, "updated": 1, "versioned": 1}
    assert len(client.tables["regulation_versions"]) == 2
