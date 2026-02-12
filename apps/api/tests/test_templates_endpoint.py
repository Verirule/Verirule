import httpx
from fastapi.testclient import TestClient

from app.core import supabase_rest
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
TEMPLATE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def test_templates_list_is_public(monkeypatch) -> None:
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def get(self, url: str, params: dict[str, str], headers: dict[str, str]) -> FakeResponse:
            assert headers["apikey"] == "test-anon-key"
            assert "Authorization" not in headers

            if url == "https://example.supabase.co/rest/v1/templates":
                assert params == {
                    "select": "id,slug,name,description,default_cadence,tags,created_at",
                    "order": "name.asc",
                }
                return FakeResponse(
                    [
                        {
                            "id": TEMPLATE_ID,
                            "slug": "soc2",
                            "name": "SOC 2",
                            "description": "Core security and availability monitoring",
                            "default_cadence": "weekly",
                            "tags": ["soc2", "security"],
                            "created_at": "2026-02-10T00:00:00Z",
                        }
                    ]
                )

            if url == "https://example.supabase.co/rest/v1/template_sources":
                assert params == {
                    "select": "id,template_id,name,url,cadence,tags,created_at",
                    "order": "name.asc",
                }
                return FakeResponse(
                    [
                        {
                            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                            "template_id": TEMPLATE_ID,
                            "name": "Source 1",
                            "url": "https://example.com/one",
                            "cadence": "weekly",
                            "tags": ["soc2"],
                            "created_at": "2026-02-10T00:00:00Z",
                        },
                        {
                            "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                            "template_id": TEMPLATE_ID,
                            "name": "Source 2",
                            "url": "https://example.com/two",
                            "cadence": "daily",
                            "tags": ["soc2"],
                            "created_at": "2026-02-10T00:00:00Z",
                        },
                    ]
                )

            raise AssertionError(f"Unexpected URL: {url}")

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in templates list test")

    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    client = TestClient(app)
    response = client.get("/api/v1/templates")

    assert response.status_code == 200
    assert response.json() == {
        "templates": [
            {
                "id": TEMPLATE_ID,
                "slug": "soc2",
                "name": "SOC 2",
                "description": "Core security and availability monitoring",
                "default_cadence": "weekly",
                "tags": ["soc2", "security"],
                "source_count": 2,
                "created_at": "2026-02-10T00:00:00Z",
            }
        ]
    }


def test_templates_install_requires_auth() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/templates/soc2/install", json={"org_id": ORG_ID})
    assert response.status_code == 401


def test_templates_install_requires_org_membership(monkeypatch) -> None:
    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, json: dict[str, str], headers: dict[str, str]):
            assert url == "https://example.supabase.co/rest/v1/rpc/install_template"
            assert json == {"p_org_id": ORG_ID, "p_template_slug": "soc2"}
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"

            request = httpx.Request("POST", url)
            response = httpx.Response(
                status_code=400,
                request=request,
                json={"message": "not a member of org"},
            )
            raise httpx.HTTPStatusError("membership check failed", request=request, response=response)

        async def get(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("GET should not be called in install test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post("/api/v1/templates/soc2/install", json={"org_id": ORG_ID})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code in (400, 403)
    assert "member" in response.json().get("detail", "").lower()
