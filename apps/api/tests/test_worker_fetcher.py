import asyncio
import ipaddress

import pytest

from app.worker import fetcher


def test_validate_fetch_url_rejects_private_ip_ranges() -> None:
    with pytest.raises(fetcher.UnsafeUrlError):
        fetcher.validate_fetch_url("http://127.0.0.1/internal")

    with pytest.raises(fetcher.UnsafeUrlError):
        fetcher.validate_fetch_url("http://169.254.169.254/latest/meta-data")


def test_validate_fetch_url_respects_allowed_hosts(monkeypatch) -> None:
    monkeypatch.setattr(fetcher, "resolve_public_ips", lambda host: [ipaddress.ip_address("140.82.114.5")])

    assert (
        fetcher.validate_fetch_url(
            "https://api.github.com/repos/openai/openai-python/releases",
            allowed_hosts={"api.github.com"},
        )
        == "https://api.github.com/repos/openai/openai-python/releases"
    )

    with pytest.raises(fetcher.UnsafeUrlError):
        fetcher.validate_fetch_url(
            "https://example.com/feed.xml",
            allowed_hosts={"api.github.com"},
        )


def test_fetch_url_handles_304_not_modified(monkeypatch) -> None:
    class FakeResponse:
        status_code = 304
        headers = {
            "etag": '"etag-v2"',
            "last-modified": "Thu, 11 Feb 2026 00:00:00 GMT",
            "content-type": "text/html",
        }
        url = "https://example.com/policy"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        async def aiter_bytes(self):
            yield b""

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            assert kwargs["follow_redirects"] is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        def stream(self, method: str, url: str, headers: dict[str, str]) -> FakeResponse:
            assert method == "GET"
            assert url == "https://example.com/policy"
            assert headers["If-None-Match"] == '"etag-v1"'
            assert headers["If-Modified-Since"] == "Wed, 10 Feb 2026 00:00:00 GMT"
            return FakeResponse()

    monkeypatch.setattr(fetcher, "resolve_public_ips", lambda host: [ipaddress.ip_address("93.184.216.34")])
    monkeypatch.setattr(fetcher.httpx, "AsyncClient", FakeAsyncClient)

    result = asyncio.run(
        fetcher.fetch_url(
            "https://example.com/policy",
            etag='"etag-v1"',
            last_modified="Wed, 10 Feb 2026 00:00:00 GMT",
        )
    )

    assert result["status"] == 304
    assert result["bytes"] == b""
    assert result["etag"] == '"etag-v2"'
