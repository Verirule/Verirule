from fastapi.testclient import TestClient

from app.api.v1.endpoints import controls as controls_endpoint
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
FINDING_ID = "22222222-2222-2222-2222-222222222222"
CONTROL_ID = "33333333-3333-3333-3333-333333333333"


def test_controls_list_returns_catalog(monkeypatch) -> None:
    async def fake_list_controls(access_token: str, framework_slug: str | None = None):
        assert access_token == "token-123"
        assert framework_slug == "gdpr"
        return [
            {
                "id": CONTROL_ID,
                "framework_slug": "gdpr",
                "control_key": "GDPR-32",
                "title": "Security of Processing",
                "description": "Appropriate safeguards are implemented.",
                "severity_default": "high",
                "tags": ["gdpr", "privacy", "security"],
                "created_at": "2026-02-12T00:00:00Z",
            }
        ]

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(controls_endpoint, "list_controls", fake_list_controls)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/controls?framework=gdpr")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "controls": [
            {
                "id": CONTROL_ID,
                "framework_slug": "gdpr",
                "control_key": "GDPR-32",
                "title": "Security of Processing",
                "description": "Appropriate safeguards are implemented.",
                "severity_default": "high",
                "tags": ["gdpr", "privacy", "security"],
                "created_at": "2026-02-12T00:00:00Z",
            }
        ]
    }


def test_install_controls_from_template(monkeypatch) -> None:
    async def fake_rpc_install(access_token: str, org_id: str, template_slug: str) -> int:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert template_slug == "gdpr"
        return 10

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(controls_endpoint, "rpc_install_controls_for_template", fake_rpc_install)

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/orgs/{ORG_ID}/controls/install-from-template",
            json={"template_slug": "GDPR"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"installed": 10}


def test_link_finding_to_control(monkeypatch) -> None:
    recorded_payload: dict[str, str] = {}

    async def fake_select_finding_by_id(access_token: str, finding_id: str):
        assert access_token == "token-123"
        assert finding_id == FINDING_ID
        return {
            "id": FINDING_ID,
            "org_id": ORG_ID,
            "source_id": "44444444-4444-4444-4444-444444444444",
            "title": "Finding title",
            "summary": "Finding summary",
        }

    async def fake_rpc_link(
        access_token: str, org_id: str, finding_id: str, control_id: str, confidence: str
    ) -> None:
        recorded_payload.update(
            {
                "access_token": access_token,
                "org_id": org_id,
                "finding_id": finding_id,
                "control_id": control_id,
                "confidence": confidence,
            }
        )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(controls_endpoint, "select_finding_by_id", fake_select_finding_by_id)
    monkeypatch.setattr(controls_endpoint, "rpc_link_finding_to_control", fake_rpc_link)

    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/findings/{FINDING_ID}/controls",
            json={
                "org_id": ORG_ID,
                "control_id": CONTROL_ID,
                "confidence": "high",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert recorded_payload == {
        "access_token": "token-123",
        "org_id": ORG_ID,
        "finding_id": FINDING_ID,
        "control_id": CONTROL_ID,
        "confidence": "high",
    }


def test_suggest_controls_returns_stable_ranking(monkeypatch) -> None:
    async def fake_select_finding_by_id(access_token: str, finding_id: str):
        assert access_token == "token-123"
        assert finding_id == FINDING_ID
        return {
            "id": FINDING_ID,
            "org_id": ORG_ID,
            "source_id": "44444444-4444-4444-4444-444444444444",
            "title": "Privileged access control drift",
            "summary": "Access review failed and vulnerability patch cadence is delayed.",
            "tags": ["security", "access-control"],
        }

    async def fake_select_latest_finding_explanation(access_token: str, finding_id: str):
        assert access_token == "token-123"
        assert finding_id == FINDING_ID
        return {
            "id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "org_id": ORG_ID,
            "finding_id": FINDING_ID,
            "summary": "Access logging and privileged account review show repeated gaps.",
            "diff_preview": "Access policy update missing and logging controls weakened.",
            "citations": [],
            "created_at": "2026-02-12T00:00:00Z",
        }

    async def fake_select_source_by_id(access_token: str, source_id: str):
        assert access_token == "token-123"
        assert source_id == "44444444-4444-4444-4444-444444444444"
        return {"id": source_id, "tags": ["security", "access-control"]}

    async def fake_list_org_controls(access_token: str, org_id: str):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        return []

    async def fake_list_controls(access_token: str, framework_slug: str | None = None):
        assert access_token == "token-123"
        assert framework_slug is None
        return [
            {
                "id": CONTROL_ID,
                "framework_slug": "soc2",
                "control_key": "CC6.1",
                "title": "Logical Access Security",
                "description": "Restrict logical access and manage privileged identities.",
                "severity_default": "high",
                "tags": ["soc2", "security", "access-control"],
                "created_at": "2026-02-12T00:00:00Z",
            },
            {
                "id": "99999999-9999-9999-9999-999999999999",
                "framework_slug": "gdpr",
                "control_key": "GDPR-32",
                "title": "Security of Processing",
                "description": "Apply technical and organizational security safeguards.",
                "severity_default": "high",
                "tags": ["gdpr", "privacy"],
                "created_at": "2026-02-12T00:00:00Z",
            },
        ]

    async def fake_list_finding_controls(access_token: str, org_id: str, finding_id: str):
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert finding_id == FINDING_ID
        return []

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(controls_endpoint, "select_finding_by_id", fake_select_finding_by_id)
    monkeypatch.setattr(
        controls_endpoint, "select_latest_finding_explanation", fake_select_latest_finding_explanation
    )
    monkeypatch.setattr(controls_endpoint, "select_source_by_id", fake_select_source_by_id)
    monkeypatch.setattr(controls_endpoint, "list_org_controls", fake_list_org_controls)
    monkeypatch.setattr(controls_endpoint, "list_controls", fake_list_controls)
    monkeypatch.setattr(controls_endpoint, "list_finding_controls", fake_list_finding_controls)

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/findings/{FINDING_ID}/controls/suggest?org_id={ORG_ID}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("suggestions"), list)
    assert body["suggestions"][0]["control_key"] == "CC6.1"
    assert body["suggestions"][0]["confidence"] in {"high", "medium"}

