from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class RegulationItem:
    title: str
    summary: str
    source: str
    source_url: str
    jurisdiction: str
    industry: str
    published_at: datetime | None
    raw_text: str


class BaseRegulationSource(ABC):
    """Abstract base class for regulation sources."""

    source_name: str
    jurisdiction: str
    industry: str

    @abstractmethod
    def fetch(self) -> List[dict]:
        """Return normalized regulation items."""
        raise NotImplementedError

    @staticmethod
    def normalize(item: RegulationItem) -> dict:
        return {
            "title": item.title,
            "summary": item.summary,
            "source": item.source,
            "source_url": item.source_url,
            "jurisdiction": item.jurisdiction,
            "industry": item.industry,
            "published_at": item.published_at,
            "raw_text": item.raw_text,
        }
