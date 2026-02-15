from fastapi.testclient import TestClient

from app.api.v1.endpoints import automation as automation_endpoint
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
ALERT_ID = "22222222-2222-2222-2222-222222222222"
FINDING_ID = "33333333-3333-3333-3333-333333333333"
TASK_ID = "44444444-4444-4444-4444-444444444444"


def test_create_task_now_returns_existing_task(monkeypatch) -> None:
    async def fake_select_alert(access_token: str, org_id: str, alert_id: str):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert alert_id == ALERT_ID
        return {
            "id": ALERT_ID,
            "org_id": ORG_ID,
            "finding_id": FINDING_ID,
            "task_id": TASK_ID,
            "status": "open",
        }

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(automation_endpoint, "select_alert_by_id_for_org", fake_select_alert)

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/alerts/{ALERT_ID}/create-task-now",
            json={"org_id": ORG_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"task_id": TASK_ID}


def test_create_task_now_creates_and_links_task(monkeypatch) -> None:
    links: list[tuple[str, str, str]] = []
    evidences: list[dict[str, str]] = []
    updates: list[dict[str, object]] = []

    async def fake_select_alert(access_token: str, org_id: str, alert_id: str):
        return {
            "id": ALERT_ID,
            "org_id": org_id,
            "finding_id": FINDING_ID,
            "task_id": None,
            "status": "open",
            "created_at": "2026-02-13T00:00:00Z",
        }

    async def fake_select_finding(access_token: str, finding_id: str):
        assert finding_id == FINDING_ID
        return {
            "id": FINDING_ID,
            "org_id": ORG_ID,
            "source_id": "55555555-5555-5555-5555-555555555555",
            "title": "TLS policy changed",
            "summary": "Certificate verification requirements were updated.",
            "severity": "high",
            "raw_url": "https://example.com/policy",
        }

    async def fake_create_task(access_token: str, payload: dict[str, object]) -> str:
        assert payload["p_org_id"] == ORG_ID
        assert payload["p_alert_id"] == ALERT_ID
        assert payload["p_finding_id"] == FINDING_ID
        assert payload["p_due_at"] == "2026-02-14T00:00:00Z"
        return TASK_ID

    async def fake_compute_due_at(
        access_token: str,
        *,
        org_id: str,
        severity: str,
        created_at: str | None,
    ) -> str:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert severity == "high"
        assert created_at == "2026-02-13T00:00:00Z"
        return "2026-02-14T00:00:00Z"

    async def fake_update_task(task_id: str, patch: dict[str, object]) -> None:
        updates.append({"task_id": task_id, "patch": patch})

    async def fake_link_alert(access_token: str, org_id: str, alert_id: str, task_id: str) -> None:
        links.append((org_id, alert_id, task_id))

    async def fake_ensure(access_token: str, org_id: str) -> None:
        return None

    async def fake_rules(access_token: str, org_id: str):
        return {
            "org_id": org_id,
            "enabled": True,
            "auto_create_task_on_alert": True,
            "min_severity": "medium",
            "auto_link_suggested_controls": True,
            "auto_add_evidence_checklist": True,
            "created_at": "2026-02-13T00:00:00Z",
            "updated_at": "2026-02-13T00:00:00Z",
        }

    async def fake_resolve_controls(*args, **kwargs):
        return ["66666666-6666-6666-6666-666666666666"]

    async def fake_insert_task_controls(access_token: str, org_id: str, task_id: str, control_ids: list[str]) -> int:
        assert org_id == ORG_ID
        assert task_id == TASK_ID
        assert control_ids == ["66666666-6666-6666-6666-666666666666"]
        return 1

    async def fake_evidence_items(access_token: str, control_ids: list[str]):
        assert control_ids == ["66666666-6666-6666-6666-666666666666"]
        return [
            {
                "control_id": control_ids[0],
                "label": "Retention policy record",
                "description": "Provide current retention policy",
                "evidence_type": "document",
                "required": True,
            }
        ]

    async def fake_add_task_evidence(access_token: str, payload: dict[str, str]) -> str:
        evidences.append(payload)
        return "77777777-7777-7777-7777-777777777777"

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(automation_endpoint, "select_alert_by_id_for_org", fake_select_alert)
    monkeypatch.setattr(automation_endpoint, "select_finding_by_id", fake_select_finding)
    monkeypatch.setattr(automation_endpoint, "rpc_compute_task_due_at", fake_compute_due_at)
    monkeypatch.setattr(automation_endpoint, "rpc_create_task", fake_create_task)
    monkeypatch.setattr(automation_endpoint, "update_task_service", fake_update_task)
    monkeypatch.setattr(automation_endpoint, "update_alert_task_id", fake_link_alert)
    monkeypatch.setattr(automation_endpoint, "ensure_alert_task_rules", fake_ensure)
    monkeypatch.setattr(automation_endpoint, "get_alert_task_rules", fake_rules)
    monkeypatch.setattr(automation_endpoint, "resolve_control_ids_for_alert", fake_resolve_controls)
    monkeypatch.setattr(automation_endpoint, "bulk_insert_task_controls", fake_insert_task_controls)
    monkeypatch.setattr(automation_endpoint, "list_control_evidence_items", fake_evidence_items)
    monkeypatch.setattr(automation_endpoint, "rpc_add_task_evidence", fake_add_task_evidence)

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/alerts/{ALERT_ID}/create-task-now",
            json={"org_id": ORG_ID},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"task_id": TASK_ID}
    assert links == [(ORG_ID, ALERT_ID, TASK_ID)]
    assert updates == [
        {
            "task_id": TASK_ID,
            "patch": {"severity": "high", "sla_state": "on_track"},
        }
    ]
    assert len(evidences) == 1
    assert evidences[0]["p_task_id"] == TASK_ID
