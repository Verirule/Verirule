from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.templates import TemplateInstallIn, TemplateListItemOut, TemplateSourceOut
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    rpc_install_template,
    select_template_by_slug_public,
    select_template_sources_public,
    select_templates_public,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/templates")
async def templates() -> dict[str, list[TemplateListItemOut]]:
    template_rows = await select_templates_public()
    source_rows = await select_template_sources_public()

    source_counts: dict[str, int] = {}
    for row in source_rows:
        template_id = row.get("template_id")
        if isinstance(template_id, str):
            source_counts[template_id] = source_counts.get(template_id, 0) + 1

    templates_with_counts: list[TemplateListItemOut] = []
    for row in template_rows:
        template_id = row.get("id")
        source_count = source_counts.get(template_id, 0) if isinstance(template_id, str) else 0
        templates_with_counts.append(TemplateListItemOut.model_validate({**row, "source_count": source_count}))

    return {"templates": templates_with_counts}


@router.get("/templates/{slug}")
async def template_detail(slug: str) -> dict[str, object]:
    template_row = await select_template_by_slug_public(slug)
    if template_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

    template_id = template_row.get("id")
    if not isinstance(template_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid template response from Supabase.",
        )

    source_rows = await select_template_sources_public(template_id=template_id)
    template = TemplateListItemOut.model_validate({**template_row, "source_count": len(source_rows)})
    sources = [TemplateSourceOut.model_validate(row) for row in source_rows]
    return {"template": template, "sources": sources}


@router.post("/templates/{slug}/install")
async def install_template(
    slug: str,
    payload: TemplateInstallIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, int | str]:
    installed_count = await rpc_install_template(
        auth.access_token,
        {"p_org_id": str(payload.org_id), "p_template_slug": slug},
    )
    return {"template_slug": slug, "installed": installed_count, "org_id": str(payload.org_id)}
