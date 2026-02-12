from __future__ import annotations

import hashlib
from io import BytesIO

from pypdf import PdfReader

from app.worker.adapters.base import AdapterResult, Snapshot, Source
from app.worker.fetcher import fetch_url

MAX_PDF_PAGES = 20
MAX_PDF_CHARS = 200_000


def _extract_pdf_text(content: bytes) -> tuple[str, str | None]:
    if not content:
        return "", None

    title: str | None = None
    chunks: list[str] = []
    total_chars = 0

    try:
        reader = PdfReader(BytesIO(content))
        metadata = reader.metadata
        meta_title = metadata.get("/Title") if metadata else None
        if isinstance(meta_title, str):
            cleaned_title = " ".join(meta_title.split())
            title = cleaned_title or None

        for page_index, page in enumerate(reader.pages):
            if page_index >= MAX_PDF_PAGES or total_chars >= MAX_PDF_CHARS:
                break
            page_text = page.extract_text() or ""
            cleaned_page = page_text.strip()
            if not cleaned_page:
                continue

            remaining = MAX_PDF_CHARS - total_chars
            clipped = cleaned_page[:remaining]
            chunks.append(clipped)
            total_chars += len(clipped)
    except Exception:  # pragma: no cover - defensive parser fallback
        return "", title

    return "\n".join(chunks).strip(), title


class PdfAdapter:
    async def fetch(self, source: Source, prev_snapshot: Snapshot | None) -> AdapterResult:
        fetch_result = await fetch_url(
            source.url,
            etag=source.etag or (prev_snapshot.etag if prev_snapshot else None),
            last_modified=source.last_modified or (prev_snapshot.last_modified if prev_snapshot else None),
            timeout_seconds=source.fetch_timeout_seconds,
            max_bytes=max(source.fetch_max_bytes, 5_000_000),
        )
        status_code = int(fetch_result.get("status") or 0)
        content_type = str(fetch_result.get("content_type") or "").strip() or None
        response_etag = str(fetch_result.get("etag") or "").strip() or None
        response_last_modified = str(fetch_result.get("last_modified") or "").strip() or None
        fetched_url = str(fetch_result.get("fetched_url") or source.url)

        if status_code == 304:
            previous_text = prev_snapshot.canonical_text if prev_snapshot else ""
            return AdapterResult(
                canonical_title=None,
                canonical_text=previous_text or "",
                content_type=content_type,
                etag=response_etag,
                last_modified=response_last_modified,
                http_status=status_code,
                fetched_url=fetched_url,
                content_len=0,
            )

        response_bytes = fetch_result["bytes"] if isinstance(fetch_result.get("bytes"), bytes) else b""
        raw_bytes_hash = hashlib.sha256(response_bytes).hexdigest()
        canonical_text, canonical_title = _extract_pdf_text(response_bytes)

        return AdapterResult(
            canonical_title=canonical_title,
            canonical_text=canonical_text,
            content_type=content_type,
            etag=response_etag,
            last_modified=response_last_modified,
            http_status=status_code,
            fetched_url=fetched_url,
            content_len=len(response_bytes),
            raw_bytes_hash=raw_bytes_hash,
        )
