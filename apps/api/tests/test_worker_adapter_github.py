import asyncio
import json

from app.worker.adapters.base import Source
from app.worker.adapters.github_releases import GitHubReleasesAdapter


def test_github_releases_adapter_parses_latest_release(monkeypatch) -> None:
    observed_kwargs = {}
    releases = [
        {
            "id": 100,
            "tag_name": "v1.2.0",
            "name": "Release 1.2.0",
            "body": "## Added\n- [Docs](https://example.com)\n- Fixes",
            "published_at": "2026-02-10T00:00:00Z",
        },
        {
            "id": 101,
            "tag_name": "v1.3.0",
            "name": "Release 1.3.0",
            "body": "### Highlights\n* Better parser\n`code`",
            "published_at": "2026-02-12T00:00:00Z",
        },
    ]

    async def fake_fetch(url: str, **kwargs):
        observed_kwargs.update(kwargs)
        assert url == "https://api.github.com/repos/openai/openai-python/releases"
        return {
            "status": 200,
            "bytes": json.dumps(releases).encode("utf-8"),
            "content_type": "application/json",
            "etag": '"etag-1"',
            "last_modified": "Thu, 12 Feb 2026 00:00:00 GMT",
            "fetched_url": url,
        }

    monkeypatch.setattr("app.worker.adapters.github_releases.fetch_url", fake_fetch)

    source = Source(
        id="source-1",
        org_id="org-1",
        url="https://ignored.example.com",
        kind="github_releases",
        config={"repo": "openai/openai-python"},
    )

    result = asyncio.run(GitHubReleasesAdapter().fetch(source, None))

    assert observed_kwargs["allowed_hosts"] == {"api.github.com"}
    assert observed_kwargs["extra_headers"]["User-Agent"] == "verirule"
    assert result.item_id == "101"
    assert result.canonical_title == "Release 1.3.0"
    assert "Highlights" in result.canonical_text
    assert "code" in result.canonical_text


def test_github_releases_adapter_requires_repo() -> None:
    source = Source(
        id="source-1",
        org_id="org-1",
        url="https://ignored.example.com",
        kind="github_releases",
        config={},
    )

    try:
        asyncio.run(GitHubReleasesAdapter().fetch(source, None))
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "config.repo" in str(exc)
