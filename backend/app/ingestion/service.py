from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable

from supabase import Client

from .base import RegulationItem


def _hash_content(raw_text: str) -> str:
    return hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _pick_lookup(item: RegulationItem) -> tuple[str, str]:
    if item.source_url:
        return ("source_url", item.source_url)
    return ("title", item.title)


def upsert_regulations(
    supabase: Client, items: Iterable[RegulationItem]
) -> dict:
    created = 0
    updated = 0
    versioned = 0

    for item in items:
        lookup_field, lookup_value = _pick_lookup(item)
        existing = (
            supabase.table("regulations")
            .select("id, raw_text")
            .eq(lookup_field, lookup_value)
            .limit(1)
            .execute()
        )
        data = existing.data[0] if existing.data else None

        raw_hash = _hash_content(item.raw_text)
        now = _utc_now()

        if data is None:
            insert_payload = {
                "title": item.title,
                "summary": item.summary,
                "source": item.source,
                "source_url": item.source_url,
                "jurisdiction": item.jurisdiction,
                "industry": item.industry,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "last_updated_at": now.isoformat(),
                "raw_text": item.raw_text,
                "created_at": now.isoformat(),
            }
            inserted = supabase.table("regulations").insert(insert_payload).execute()
            if inserted.data:
                regulation_id = inserted.data[0]["id"]
                supabase.table("regulation_versions").insert(
                    {
                        "regulation_id": regulation_id,
                        "content_hash": raw_hash,
                        "raw_text": item.raw_text,
                        "detected_at": now.isoformat(),
                    }
                ).execute()
                created += 1
                versioned += 1
            continue

        regulation_id = data["id"]
        versions = (
            supabase.table("regulation_versions")
            .select("content_hash")
            .eq("regulation_id", regulation_id)
            .order("detected_at", desc=True)
            .limit(1)
            .execute()
        )
        latest_hash = versions.data[0]["content_hash"] if versions.data else None
        if latest_hash != raw_hash:
            supabase.table("regulation_versions").insert(
                {
                    "regulation_id": regulation_id,
                    "content_hash": raw_hash,
                    "raw_text": item.raw_text,
                    "detected_at": now.isoformat(),
                }
            ).execute()
            supabase.table("regulations").update(
                {
                    "summary": item.summary,
                    "source": item.source,
                    "source_url": item.source_url,
                    "jurisdiction": item.jurisdiction,
                    "industry": item.industry,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "last_updated_at": now.isoformat(),
                    "raw_text": item.raw_text,
                }
            ).eq("id", regulation_id).execute()
            updated += 1
            versioned += 1

    return {"created": created, "updated": updated, "versioned": versioned}
