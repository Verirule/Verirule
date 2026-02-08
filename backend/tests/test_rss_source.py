from app.ingestion.rss_source import RssRegulationSource


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class FakeClient:
    def __init__(self, text):
        self._text = text

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url):
        return FakeResponse(self._text)


FEED = """
<rss version="2.0">
  <channel>
    <title>Reg Feed</title>
    <item>
      <title>Rule One</title>
      <description>Summary one</description>
      <link>https://example.com/rule-one</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""


def test_rss_source_parses_items(monkeypatch):
    monkeypatch.setattr("app.ingestion.rss_source.httpx.Client", lambda timeout: FakeClient(FEED))
    source = RssRegulationSource("https://example.com/feed", "rss")
    items = list(source.fetch())

    assert len(items) == 1
    item = items[0]
    assert item.title == "Rule One"
    assert item.summary == "Summary one"
    assert item.source_url == "https://example.com/rule-one"
