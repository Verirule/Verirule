from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any

import feedparser

from app.worker.adapters.base import AdapterResult, Snapshot, Source
from app.worker.fetcher import fetch_url


class _TextStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self._chunks.append(cleaned)

    def text(self) -> str:
        return "\n".join(self._chunks)


def _strip_to_text(value: str) -> str:
    parser = _TextStripper()
    parser.feed(value)
    return parser.text().strip()


def _safe_string(value: Any) -> str:
    return str(value).strip() if isinstance(value, str) else ""


def _entry_item_id(entry: Any) -> str:
    for key in ("id", "guid", "link"):
        candidate = _safe_string(entry.get(key))
        if candidate:
            return candidate

    title = _safe_string(entry.get("title"))
    published = _safe_string(entry.get("published")) or _safe_string(entry.get("updated"))
    return hashlib.sha256(f"{title}|{published}".encode()).hexdigest()


def _entry_published_at(entry: Any) -> datetime | None:
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published_parsed:
        return None
    try:
        return datetime.fromtimestamp(time.mktime(published_parsed), tz=UTC)
    except (OverflowError, TypeError, ValueError):
        return None


def _entry_text(entry: Any) -> str:
    summary = _safe_string(entry.get("summary"))
    if summary:
        return _strip_to_text(summary)

    content = entry.get("content")
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict):
                value = _safe_string(item.get("value"))
                if value:
                    chunks.append(_strip_to_text(value))
        joined = "\n".join(chunk for chunk in chunks if chunk)
        if joined:
            return joined

    title = _safe_string(entry.get("title"))
    return title


def _sorted_entries(entries: list[Any]) -> list[Any]:
    return sorted(
        entries,
        key=lambda item: _entry_published_at(item) or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )


class RssAdapter:
    async def fetch(self, source: Source, prev_snapshot: Snapshot | None) -> AdapterResult:
        fetch_result = await fetch_url(
            source.url,
            etag=source.etag or (prev_snapshot.etag if prev_snapshot else None),
            last_modified=source.last_modified or (prev_snapshot.last_modified if prev_snapshot else None),
            timeout_seconds=source.fetch_timeout_seconds,
            max_bytes=source.fetch_max_bytes,
        )
        status_code = int(fetch_result.get("status") or 0)
        content_type = str(fetch_result.get("content_type") or "").strip() or None
        response_etag = str(fetch_result.get("etag") or "").strip() or None
        response_last_modified = str(fetch_result.get("last_modified") or "").strip() or None
        fetched_url = str(fetch_result.get("fetched_url") or source.url)

        if status_code == 304:
            return AdapterResult(
                canonical_title=None,
                canonical_text="",
                item_id=prev_snapshot.item_id if prev_snapshot else None,
                item_published_at=prev_snapshot.item_published_at if prev_snapshot else None,
                content_type=content_type,
                etag=response_etag,
                last_modified=response_last_modified,
                http_status=status_code,
                fetched_url=fetched_url,
                content_len=0,
            )

        response_bytes = fetch_result["bytes"] if isinstance(fetch_result.get("bytes"), bytes) else b""
        parsed_feed = feedparser.parse(response_bytes)
        entries_raw = list(getattr(parsed_feed, "entries", []) or [])
        entries = _sorted_entries(entries_raw)

        previous_item_id = prev_snapshot.item_id if prev_snapshot else None
        selected_entry = None
        if previous_item_id:
            for entry in entries:
                if _entry_item_id(entry) != previous_item_id:
                    selected_entry = entry
                    break
        elif entries:
            selected_entry = entries[0]

        if selected_entry is None:
            return AdapterResult(
                canonical_title=None,
                canonical_text="",
                item_id=previous_item_id,
                item_published_at=prev_snapshot.item_published_at if prev_snapshot else None,
                content_type=content_type,
                etag=response_etag,
                last_modified=response_last_modified,
                http_status=status_code,
                fetched_url=fetched_url,
                content_len=len(response_bytes),
                raw_bytes_hash=hashlib.sha256(response_bytes).hexdigest(),
            )

        return AdapterResult(
            canonical_title=_safe_string(selected_entry.get("title")) or None,
            canonical_text=_entry_text(selected_entry),
            item_id=_entry_item_id(selected_entry),
            item_published_at=_entry_published_at(selected_entry),
            content_type=content_type,
            etag=response_etag,
            last_modified=response_last_modified,
            http_status=status_code,
            fetched_url=fetched_url,
            content_len=len(response_bytes),
            raw_bytes_hash=hashlib.sha256(response_bytes).hexdigest(),
        )
