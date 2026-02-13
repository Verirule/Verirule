from fastapi.testclient import TestClient

from app.api.v1.endpoints import readiness as readiness_endpoint
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
SNAPSHOT_ID = "22222222-2222-2222-2222-222222222222"


def _snapshot_payload() -> dict[str, object]:
    return {
        "id": SNAPSHOT_ID,
        "org_id": ORG_ID,
        "computed_at": "2026-02-13T00:00:00Z",
        "score": 78,
        "controls_total": 20,
        "controls_with_evidence": 12,
        "evidence_items_total": 40,
        "evidence_items_done": 24,
        "open_alerts_high": 2,
        "open_tasks": 5,
        "overdue_tasks": 1,
        "metadata": {
            "control_coverage_pct": 60,
            "evidence_completion_pct": 60,
        },
    }


def test_compute_readiness_returns_latest_snapshot(monkeypatch) -> None:
    called: list[tuple[str, str]] = []

    async def fake_rpc_compute(access_token: str, org_id: str) -> str:
        called.append((access_token, org_id))
        return SNAPSHOT_ID

    async def fake_get_latest(access_token: str, org_id: str) -> dict[str, object] | None:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return _snapshot_payload()

    monkeypatch.setattr(readiness_endpoint, "rpc_compute_org_readiness", fake_rpc_compute)
    monkeypatch.setattr(readiness_endpoint, "get_latest_org_readiness", fake_get_latest)
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(f"/api/v1/orgs/{ORG_ID}/readiness/compute")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_id"] == SNAPSHOT_ID
    assert body["readiness"]["id"] == SNAPSHOT_ID
    assert called == [("token-123", ORG_ID)]


def test_list_readiness_returns_snapshots(monkeypatch) -> None:
    async def fake_list(access_token: str, org_id: str, limit: int = 30) -> list[dict[str, object]]:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert limit == 15
        return [_snapshot_payload()]

    monkeypatch.setattr(readiness_endpoint, "list_org_readiness", fake_list)
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/readiness", params={"limit": 15})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"snapshots": [_snapshot_payload()]}


def test_latest_readiness_returns_404_when_missing(monkeypatch) -> None:
    async def fake_get_latest(access_token: str, org_id: str) -> None:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return None

    monkeypatch.setattr(readiness_endpoint, "get_latest_org_readiness", fake_get_latest)
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/readiness/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Readiness snapshot not found."}
