from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from app.worker.adapters.base import AdapterResult, Snapshot, Source
from app.worker.fetcher import fetch_url

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _to_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    text = value
    text = re.sub(r"```[\s\S]*?```", " ", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(^|\n)#+\s*", "\n", text)
    text = re.sub(r"[*_~>-]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _release_item_id(release: dict[str, Any]) -> str:
    release_id = release.get("id")
    if isinstance(release_id, int):
        return str(release_id)
    tag_name = release.get("tag_name")
    if isinstance(tag_name, str) and tag_name.strip():
        return tag_name.strip()
    return ""


class GitHubReleasesAdapter:
    async def fetch(self, source: Source, prev_snapshot: Snapshot | None) -> AdapterResult:
        repo = str(source.config.get("repo") or "").strip()
        if not _REPO_RE.match(repo):
            raise ValueError("github_releases sources require config.repo in owner/name format")

        fetch_result = await fetch_url(
            f"https://api.github.com/repos/{repo}/releases",
            etag=source.etag or (prev_snapshot.etag if prev_snapshot else None),
            last_modified=source.last_modified or (prev_snapshot.last_modified if prev_snapshot else None),
            timeout_seconds=source.fetch_timeout_seconds,
            max_bytes=source.fetch_max_bytes,
            allowed_hosts={"api.github.com"},
            extra_headers={
                "User-Agent": "verirule",
                "Accept": "application/vnd.github+json",
            },
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
        try:
            parsed = json.loads(response_bytes.decode("utf-8", errors="replace"))
        except json.JSONDecodeError:
            parsed = []

        releases = [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []
        latest_release: dict[str, Any] | None = None
        latest_published_at: datetime | None = None
        for release in releases:
            published_at = _parse_datetime(release.get("published_at")) or _parse_datetime(
                release.get("created_at")
            )
            if latest_release is None:
                latest_release = release
                latest_published_at = published_at
                continue

            if published_at is None:
                continue
            if latest_published_at is None or published_at > latest_published_at:
                latest_release = release
                latest_published_at = published_at

        if latest_release is None:
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
                content_len=len(response_bytes),
            )

        item_id = _release_item_id(latest_release) or (prev_snapshot.item_id if prev_snapshot else None)
        tag_name = latest_release.get("tag_name")
        release_name = latest_release.get("name")
        canonical_title = (
            release_name.strip()
            if isinstance(release_name, str) and release_name.strip()
            else tag_name.strip()
            if isinstance(tag_name, str) and tag_name.strip()
            else None
        )

        return AdapterResult(
            canonical_title=canonical_title,
            canonical_text=_to_text(latest_release.get("body")),
            item_id=item_id,
            item_published_at=_parse_datetime(latest_release.get("published_at"))
            or _parse_datetime(latest_release.get("created_at")),
            content_type=content_type,
            etag=response_etag,
            last_modified=response_last_modified,
            http_status=status_code,
            fetched_url=fetched_url,
            content_len=len(response_bytes),
        )
