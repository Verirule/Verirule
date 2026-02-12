from __future__ import annotations

from app.worker.adapters.base import Adapter
from app.worker.adapters.github_releases import GitHubReleasesAdapter
from app.worker.adapters.html import HtmlAdapter
from app.worker.adapters.pdf import PdfAdapter
from app.worker.adapters.rss import RssAdapter

_ADAPTERS: dict[str, Adapter] = {
    "html": HtmlAdapter(),
    "rss": RssAdapter(),
    "pdf": PdfAdapter(),
    "github_releases": GitHubReleasesAdapter(),
}


def get_adapter(kind: str) -> Adapter:
    normalized_kind = (kind or "html").strip().lower()
    adapter = _ADAPTERS.get(normalized_kind)
    if adapter is None:
        raise ValueError(f"unsupported source kind: {kind}")
    return adapter
