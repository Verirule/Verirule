import asyncio

from app.worker.adapters.base import Snapshot, Source
from app.worker.adapters.rss import RssAdapter


def test_rss_adapter_selects_new_item(monkeypatch) -> None:
    feed_xml = b"""
    <rss version="2.0">
      <channel>
        <item>
          <guid>old-1</guid>
          <title>Old post</title>
          <pubDate>Wed, 11 Feb 2026 00:00:00 GMT</pubDate>
          <description>Old body</description>
        </item>
        <item>
          <guid>new-2</guid>
          <title>New post</title>
          <pubDate>Thu, 12 Feb 2026 00:00:00 GMT</pubDate>
          <description><p>New <strong>body</strong></p></description>
        </item>
      </channel>
    </rss>
    """

    async def fake_fetch(*args, **kwargs):
        return {
            "status": 200,
            "bytes": feed_xml,
            "content_type": "application/rss+xml",
            "etag": None,
            "last_modified": None,
            "fetched_url": "https://example.com/feed.xml",
        }

    monkeypatch.setattr("app.worker.adapters.rss.fetch_url", fake_fetch)

    source = Source(
        id="source-1",
        org_id="org-1",
        url="https://example.com/feed.xml",
        kind="rss",
        config={},
    )
    previous = Snapshot(item_id="old-1")
    result = asyncio.run(RssAdapter().fetch(source, previous))

    assert result.item_id == "new-2"
    assert result.canonical_title == "New post"
    assert result.canonical_text == "New\nbody"


def test_rss_adapter_dedupes_when_no_new_item(monkeypatch) -> None:
    feed_xml = b"""
    <rss version="2.0">
      <channel>
        <item>
          <guid>same-1</guid>
          <title>Same post</title>
          <pubDate>Thu, 12 Feb 2026 00:00:00 GMT</pubDate>
          <description>Same body</description>
        </item>
      </channel>
    </rss>
    """

    async def fake_fetch(*args, **kwargs):
        return {
            "status": 200,
            "bytes": feed_xml,
            "content_type": "application/rss+xml",
            "etag": None,
            "last_modified": None,
            "fetched_url": "https://example.com/feed.xml",
        }

    monkeypatch.setattr("app.worker.adapters.rss.fetch_url", fake_fetch)

    source = Source(
        id="source-1",
        org_id="org-1",
        url="https://example.com/feed.xml",
        kind="rss",
        config={},
    )
    previous = Snapshot(item_id="same-1")
    result = asyncio.run(RssAdapter().fetch(source, previous))

    assert result.item_id == "same-1"
    assert result.canonical_text == ""
