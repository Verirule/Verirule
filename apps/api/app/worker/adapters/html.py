from __future__ import annotations

import hashlib
import re
from html import unescape

from app.worker.adapters.base import AdapterResult, Snapshot, Source
from app.worker.fetcher import fetch_url
from app.worker.normalize import normalize

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _extract_title(content: bytes) -> str | None:
    decoded = content.decode("utf-8", errors="replace")
    matched = _TITLE_RE.search(decoded)
    if not matched:
        return None
    cleaned = " ".join(unescape(matched.group(1)).split())
    return cleaned or None


class HtmlAdapter:
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
            previous_text = ""
            if prev_snapshot:
                previous_text = prev_snapshot.canonical_text or prev_snapshot.text_preview or ""
            return AdapterResult(
                canonical_title=None,
                canonical_text=previous_text,
                content_type=content_type,
                etag=response_etag,
                last_modified=response_last_modified,
                http_status=status_code,
                fetched_url=fetched_url,
                content_len=0,
            )

        response_bytes = fetch_result["bytes"] if isinstance(fetch_result.get("bytes"), bytes) else b""
        normalized = normalize(content_type, response_bytes)
        return AdapterResult(
            canonical_title=_extract_title(response_bytes),
            canonical_text=str(normalized.get("normalized_text") or ""),
            content_type=content_type,
            etag=response_etag,
            last_modified=response_last_modified,
            http_status=status_code,
            fetched_url=fetched_url,
            content_len=len(response_bytes),
            raw_bytes_hash=hashlib.sha256(response_bytes).hexdigest(),
        )
