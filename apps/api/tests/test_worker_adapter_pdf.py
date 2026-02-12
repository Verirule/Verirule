import asyncio
import hashlib
from io import BytesIO

from pypdf import PdfWriter

from app.worker.adapters.base import Source
from app.worker.adapters.pdf import PdfAdapter


def _build_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_metadata({"/Title": "Example PDF"})
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_pdf_adapter_hashes_bytes_when_text_empty(monkeypatch) -> None:
    pdf_bytes = _build_pdf_bytes()

    async def fake_fetch(*args, **kwargs):
        return {
            "status": 200,
            "bytes": pdf_bytes,
            "content_type": "application/pdf",
            "etag": None,
            "last_modified": None,
            "fetched_url": "https://example.com/policy.pdf",
        }

    monkeypatch.setattr("app.worker.adapters.pdf.fetch_url", fake_fetch)

    source = Source(
        id="source-1",
        org_id="org-1",
        url="https://example.com/policy.pdf",
        kind="pdf",
        config={},
    )

    result = asyncio.run(PdfAdapter().fetch(source, None))

    assert result.canonical_text == ""
    assert result.canonical_title == "Example PDF"
    assert result.raw_bytes_hash == hashlib.sha256(pdf_bytes).hexdigest()
