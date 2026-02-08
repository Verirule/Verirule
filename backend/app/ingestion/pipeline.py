from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable

from supabase import Client

from ..config import Settings
from ..supabase_client import get_supabase_service_client
from .base import BaseRegulationSource
from .rss_source import RssRegulationSource
from .utils import hash_raw_text, has_content_changed

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _select_latest_hash(client: Client, regulation_id: str) -> str | None:
    result = (
        client.table("regulation_versions")
        .select("content_hash")
        .eq("regulation_id", regulation_id)
        .order("detected_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0]["content_hash"] if result.data else None


def _get_regulation_by_source_url(client: Client, source_url: str) -> dict | None:
    result = (
        client.table("regulations")
        .select("id")
        .eq("source_url", source_url)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def run_ingestion(
    settings: Settings,
    source: BaseRegulationSource | None = None,
    client: Client | None = None,
) -> Dict[str, int]:
    """Run ingestion pipeline and return summary stats."""
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for ingestion")

    if client is None:
        client = get_supabase_service_client(settings)

    if source is None:
        source = RssRegulationSource(
            feed_url=settings.INGESTION_FEED_URL,
            source_name="rss",
            jurisdiction="",
            industry="",
        )

    items = source.fetch()
    fetched = len(items)
    inserted = 0
    updated = 0
    skipped = 0

    for item in items:
        source_url = item.get("source_url")
        if not source_url:
            skipped += 1
            continue

        existing = _get_regulation_by_source_url(client, source_url)
        now = _utc_now()
        raw_text = item.get("raw_text", "")
        content_hash = hash_raw_text(raw_text)

        if existing is None:
            insert_payload = {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "source": item.get("source"),
                "source_url": source_url,
                "jurisdiction": item.get("jurisdiction"),
                "industry": item.get("industry"),
                "published_at": item.get("published_at").isoformat()
                if item.get("published_at")
                else None,
                "last_updated_at": now.isoformat(),
                "raw_text": raw_text,
                "created_at": now.isoformat(),
            }
            result = client.table("regulations").insert(insert_payload).execute()
            if not result.data:
                logger.error("Failed to insert regulation for %s", source_url)
                skipped += 1
                continue

            regulation_id = result.data[0]["id"]
            client.table("regulation_versions").insert(
                {
                    "regulation_id": regulation_id,
                    "content_hash": content_hash,
                    "raw_text": raw_text,
                    "detected_at": now.isoformat(),
                }
            ).execute()
            inserted += 1
            continue

        regulation_id = existing["id"]
        latest_hash = _select_latest_hash(client, regulation_id)
        if has_content_changed(content_hash, latest_hash):
            client.table("regulation_versions").insert(
                {
                    "regulation_id": regulation_id,
                    "content_hash": content_hash,
                    "raw_text": raw_text,
                    "detected_at": now.isoformat(),
                }
            ).execute()
            client.table("regulations").update(
                {"last_updated_at": now.isoformat(), "raw_text": raw_text}
            ).eq("id", regulation_id).execute()
            updated += 1
        else:
            skipped += 1

    return {
        "fetched": fetched,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }
