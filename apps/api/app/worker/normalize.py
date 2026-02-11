from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from html.parser import HTMLParser
from typing import Any


class _VisibleTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self._chunks.append(cleaned)

    def text(self) -> str:
        return "\n".join(self._chunks)


def _extract_html_text(content: bytes) -> str:
    decoded = content.decode("utf-8", errors="replace")
    parser = _VisibleTextExtractor()
    parser.feed(decoded)
    return parser.text()


def _extract_pdf_text(content: bytes) -> str:
    decoded = content.decode("latin-1", errors="ignore")
    matches = re.findall(r"\(([^()]*)\)", decoded)
    if not matches:
        return ""
    chunks = []
    for item in matches[:2000]:
        text = unescape(item.replace("\\n", " ").replace("\\r", " ").replace("\\t", " "))
        cleaned = " ".join(text.split())
        if cleaned:
            chunks.append(cleaned)
    return "\n".join(chunks)


def normalize(content_type: str | None, content: bytes) -> dict[str, Any]:
    normalized_text = ""
    lowered_content_type = (content_type or "").lower()

    if "text/html" in lowered_content_type:
        normalized_text = _extract_html_text(content)
    elif "application/json" in lowered_content_type:
        decoded = content.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(decoded)
            normalized_text = json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True)
        except json.JSONDecodeError:
            normalized_text = decoded
    elif lowered_content_type.startswith("text/"):
        normalized_text = content.decode("utf-8", errors="replace")
    elif "application/pdf" in lowered_content_type:
        normalized_text = _extract_pdf_text(content)

    normalized_text = normalized_text.strip()
    text_preview = normalized_text[:2000]
    text_fingerprint = hashlib.sha256(
        normalized_text.encode("utf-8") if normalized_text else content
    ).hexdigest()

    return {
        "normalized_text": normalized_text,
        "text_preview": text_preview,
        "text_fingerprint": text_fingerprint,
    }
