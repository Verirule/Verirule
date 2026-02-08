from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Iterable
from xml.etree import ElementTree as ET

import httpx

from .base import BaseRegulationSource, RegulationItem


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class RssRegulationSource(BaseRegulationSource):
    def __init__(self, feed_url: str, source_name: str):
        self.feed_url = feed_url
        self.source_name = source_name

    def fetch(self) -> Iterable[RegulationItem]:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(self.feed_url)
            response.raise_for_status()
            content = response.text

        root = ET.fromstring(content)
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else root.findall(".//item")

        for item in items:
            title = (item.findtext("title") or "").strip()
            summary = (item.findtext("description") or "").strip()
            source_url = (item.findtext("link") or "").strip()
            published_raw = (item.findtext("pubDate") or item.findtext("published") or "").strip()
            published_at = _parse_datetime(published_raw)
            if published_at and published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)

            raw_text_parts = [title, summary, source_url]
            raw_text = "\n".join([p for p in raw_text_parts if p])

            if not title and not raw_text:
                continue

            yield RegulationItem(
                title=title,
                summary=summary,
                source=self.source_name,
                source_url=source_url,
                jurisdiction="",
                industry="",
                published_at=published_at,
                raw_text=raw_text,
            )
