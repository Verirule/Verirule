from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.templates import (
    AppliedSourceOut,
    FrameworkTemplateOut,
    FrameworkTemplateSourceOut,
    TemplateApplyIn,
    TemplateApplyOut,
)
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    get_framework_template_by_slug,
    insert_sources_bulk,
    list_framework_template_sources,
    list_framework_templates,
    list_sources_by_org,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)
_ALLOWED_CADENCE = {"manual", "hourly", "daily", "weekly"}


def _normalize_url(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return ""

    parts = urlsplit(trimmed)
    normalized_path = parts.path.rstrip("/")
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            normalized_path,
            parts.query,
            "",
        )
    )


def _map_template_source_kind(kind: str) -> str:
    normalized = (kind or "web").strip().lower()
    if normalized in {"rss", "atom"}:
        return "rss"
    return "html"


@router.get("/templates")
async def templates(
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[FrameworkTemplateOut]]:
    template_rows = await list_framework_templates(auth.access_token)
    if not template_rows:
        return {"templates": []}

    source_rows = await list_framework_template_sources(auth.access_token)
    sources_by_template: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in source_rows:
        template_id = row.get("template_id")
        if isinstance(template_id, str):
            sources_by_template[template_id].append(row)

    payload: list[FrameworkTemplateOut] = []
    for template_row in template_rows:
        template_id = template_row.get("id")
        sources = []
        if isinstance(template_id, str):
            sources = [
                FrameworkTemplateSourceOut.model_validate(source_row)
                for source_row in sources_by_template.get(template_id, [])
            ]

        payload.append(FrameworkTemplateOut.model_validate({**template_row, "sources": sources}))

    return {"templates": payload}


@router.post("/templates/apply")
async def apply_template(
    payload: TemplateApplyIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> TemplateApplyOut:
    override_cadence = payload.overrides.cadence if payload.overrides else None
    if override_cadence and override_cadence not in _ALLOWED_CADENCE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cadence must be one of: manual, hourly, daily, weekly.",
        )

    template_slug = payload.template_slug.strip().lower()
    template = await get_framework_template_by_slug(auth.access_token, template_slug)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

    template_id = template.get("id")
    if not isinstance(template_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid template response from Supabase.",
        )

    template_sources = await list_framework_template_sources(auth.access_token, template_id=template_id)
    existing_sources = await list_sources_by_org(auth.access_token, str(payload.org_id))
    existing_urls = {
        _normalize_url(str(row.get("url") or ""))
        for row in existing_sources
        if isinstance(row.get("url"), str)
    }

    create_payloads: list[dict[str, object]] = []
    skipped = 0

    for source_row in template_sources:
        source_url = str(source_row.get("url") or "").strip()
        if not source_url:
            skipped += 1
            continue

        normalized_url = _normalize_url(source_url)
        if normalized_url in existing_urls:
            skipped += 1
            continue

        source_cadence = override_cadence or str(source_row.get("cadence") or "daily").strip().lower()
        if source_cadence not in _ALLOWED_CADENCE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cadence must be one of: manual, hourly, daily, weekly.",
            )

        enable_all_override = payload.overrides.enable_all if payload.overrides else None
        enabled_by_default = bool(source_row.get("enabled_by_default", True))
        is_enabled = enable_all_override if isinstance(enable_all_override, bool) else enabled_by_default

        tags_raw = source_row.get("tags")
        tags = [str(item) for item in tags_raw if isinstance(item, str)] if isinstance(tags_raw, list) else []
        source_title = str(source_row.get("title") or "").strip() or source_url

        create_payloads.append(
            {
                "name": source_title,
                "title": source_title,
                "url": source_url,
                "kind": _map_template_source_kind(str(source_row.get("kind") or "web")),
                "cadence": source_cadence,
                "tags": tags,
                "is_enabled": is_enabled,
            }
        )
        existing_urls.add(normalized_url)

    created_sources_rows = await insert_sources_bulk(
        auth.access_token,
        str(payload.org_id),
        create_payloads,
    )

    created_sources = [AppliedSourceOut.model_validate(row) for row in created_sources_rows]

    return TemplateApplyOut(
        created=len(created_sources),
        skipped=skipped,
        sources=created_sources,
        metadata={
            "org_id": str(payload.org_id),
            "template_slug": template_slug,
            "requested_by": str(auth.claims.get("sub") or ""),
        },
    )
