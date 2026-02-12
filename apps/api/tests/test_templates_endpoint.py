from fastapi.testclient import TestClient

from app.core import supabase_rest
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
TEMPLATE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def test_templates_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/templates")
    assert response.status_code == 401


def test_templates_list_returns_sources_by_template(monkeypatch) -> None:
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
            assert headers["Authorization"] == "Bearer token-123"
            assert headers["apikey"] == "test-anon-key"

            if url == "https://example.supabase.co/rest/v1/framework_templates":
                assert params == {
                    "select": "id,slug,name,description,category,is_public,created_at",
                    "is_public": "eq.true",
                    "order": "name.asc",
                }
                return FakeResponse(
                    [
                        {
                            "id": TEMPLATE_ID,
                            "slug": "gdpr",
                            "name": "GDPR",
                            "description": "Privacy updates",
                            "category": "Privacy",
                            "is_public": True,
                            "created_at": "2026-02-10T00:00:00Z",
                        }
                    ]
                )

            if url == "https://example.supabase.co/rest/v1/framework_template_sources":
                assert params == {
                    "select": "id,template_id,title,url,kind,cadence,tags,enabled_by_default,created_at",
                    "order": "title.asc",
                }
                return FakeResponse(
                    [
                        {
                            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                            "template_id": TEMPLATE_ID,
                            "title": "EDPB News",
                            "url": "https://www.edpb.europa.eu/feed/news_en",
                            "kind": "rss",
                            "cadence": "hourly",
                            "tags": ["gdpr", "privacy"],
                            "enabled_by_default": True,
                            "created_at": "2026-02-10T00:00:00Z",
                        }
                    ]
                )

            raise AssertionError(f"Unexpected URL: {url}")

        async def post(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("POST should not be called in templates list test")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.get("/api/v1/templates")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "templates": [
            {
                "id": TEMPLATE_ID,
                "slug": "gdpr",
                "name": "GDPR",
                "description": "Privacy updates",
                "category": "Privacy",
                "is_public": True,
                "created_at": "2026-02-10T00:00:00Z",
                "sources": [
                    {
                        "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                        "template_id": TEMPLATE_ID,
                        "title": "EDPB News",
                        "url": "https://www.edpb.europa.eu/feed/news_en",
                        "kind": "rss",
                        "cadence": "hourly",
                        "tags": ["gdpr", "privacy"],
                        "enabled_by_default": True,
                        "created_at": "2026-02-10T00:00:00Z",
                    }
                ],
            }
        ]
    }


def test_apply_template_creates_sources(monkeypatch) -> None:
    created_payloads: list[dict[str, object]] = []

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
            assert headers["Authorization"] == "Bearer token-123"

            if url == "https://example.supabase.co/rest/v1/framework_templates":
                assert params == {
                    "select": "id,slug,name,description,category,is_public,created_at",
                    "is_public": "eq.true",
                    "slug": "eq.gdpr",
                    "limit": "1",
                }
                return FakeResponse(
                    [
                        {
                            "id": TEMPLATE_ID,
                            "slug": "gdpr",
                            "name": "GDPR",
                            "description": "Privacy updates",
                            "category": "Privacy",
                            "is_public": True,
                            "created_at": "2026-02-10T00:00:00Z",
                        }
                    ]
                )

            if url == "https://example.supabase.co/rest/v1/framework_template_sources":
                assert params == {
                    "select": "id,template_id,title,url,kind,cadence,tags,enabled_by_default,created_at",
                    "order": "title.asc",
                    "template_id": f"eq.{TEMPLATE_ID}",
                }
                return FakeResponse(
                    [
                        {
                            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                            "template_id": TEMPLATE_ID,
                            "title": "EDPB News",
                            "url": "https://www.edpb.europa.eu/feed/news_en",
                            "kind": "rss",
                            "cadence": "hourly",
                            "tags": ["gdpr", "privacy"],
                            "enabled_by_default": True,
                            "created_at": "2026-02-10T00:00:00Z",
                        },
                        {
                            "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                            "template_id": TEMPLATE_ID,
                            "title": "GDPR Official Text",
                            "url": "https://eur-lex.europa.eu/eli/reg/2016/679/oj",
                            "kind": "web",
                            "cadence": "weekly",
                            "tags": ["gdpr", "law"],
                            "enabled_by_default": True,
                            "created_at": "2026-02-10T00:00:00Z",
                        },
                    ]
                )

            if url == "https://example.supabase.co/rest/v1/sources":
                assert params == {
                    "select": "id,org_id,name,title,url,kind,cadence,is_enabled,tags",
                    "org_id": f"eq.{ORG_ID}",
                    "order": "created_at.asc",
                }
                return FakeResponse([])

            raise AssertionError(f"Unexpected GET URL: {url}")

        async def post(self, url: str, json: dict[str, object], headers: dict[str, str]) -> FakeResponse:
            assert headers["Authorization"] == "Bearer token-123"
            if url != "https://example.supabase.co/rest/v1/rpc/create_source_v3":
                raise AssertionError(f"Unexpected POST URL: {url}")

            created_payloads.append(json)
            return FakeResponse(
                "99999999-9999-9999-9999-999999999999"
                if len(created_payloads) == 1
                else "88888888-8888-8888-8888-888888888888"
            )

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/templates/apply",
            json={
                "org_id": ORG_ID,
                "template_slug": "gdpr",
                "overrides": {"cadence": "daily", "enable_all": True},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] == 2
    assert payload["skipped"] == 0
    assert len(payload["sources"]) == 2
    assert created_payloads[0]["p_kind"] == "rss"
    assert created_payloads[0]["p_cadence"] == "daily"
    assert created_payloads[1]["p_kind"] == "html"


def test_apply_template_skips_duplicates_by_url(monkeypatch) -> None:
    post_calls = 0

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
            if url == "https://example.supabase.co/rest/v1/framework_templates":
                return FakeResponse(
                    [
                        {
                            "id": TEMPLATE_ID,
                            "slug": "gdpr",
                            "name": "GDPR",
                            "description": "Privacy updates",
                            "category": "Privacy",
                            "is_public": True,
                            "created_at": "2026-02-10T00:00:00Z",
                        }
                    ]
                )

            if url == "https://example.supabase.co/rest/v1/framework_template_sources":
                return FakeResponse(
                    [
                        {
                            "id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                            "template_id": TEMPLATE_ID,
                            "title": "EDPB News",
                            "url": "https://www.edpb.europa.eu/feed/news_en",
                            "kind": "rss",
                            "cadence": "hourly",
                            "tags": ["gdpr", "privacy"],
                            "enabled_by_default": True,
                            "created_at": "2026-02-10T00:00:00Z",
                        }
                    ]
                )

            if url == "https://example.supabase.co/rest/v1/sources":
                return FakeResponse(
                    [
                        {
                            "id": "77777777-7777-7777-7777-777777777777",
                            "org_id": ORG_ID,
                            "name": "Existing EDPB News",
                            "title": "Existing EDPB News",
                            "url": "https://www.edpb.europa.eu/feed/news_en",
                            "kind": "rss",
                            "cadence": "daily",
                            "is_enabled": True,
                            "tags": ["gdpr"],
                        }
                    ]
                )

            raise AssertionError(f"Unexpected GET URL: {url}")

        async def post(self, url: str, json: dict[str, object], headers: dict[str, str]) -> FakeResponse:
            nonlocal post_calls
            post_calls += 1
            return FakeResponse("99999999-9999-9999-9999-999999999999")

    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", FakeAsyncClient)

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/templates/apply",
            json={"org_id": ORG_ID, "template_slug": "gdpr"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["created"] == 0
    assert payload["skipped"] == 1
    assert payload["sources"] == []
    assert post_calls == 0


def test_apply_template_rejects_invalid_cadence(monkeypatch) -> None:
    app.dependency_overrides[verify_supabase_auth] = lambda: VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "user-1"},
    )

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/templates/apply",
            json={
                "org_id": ORG_ID,
                "template_slug": "gdpr",
                "overrides": {"cadence": "every-minute"},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "Cadence must be one of" in response.json().get("detail", "")
