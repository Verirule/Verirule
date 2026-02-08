from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol


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


class BaseRegulationSource(Protocol):
    def fetch(self) -> Iterable[RegulationItem]:
        ...
