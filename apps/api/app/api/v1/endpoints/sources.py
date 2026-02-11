from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.schemas.sources import SourceCreateIn, SourceOut, SourceScheduleIn, SourceToggleIn
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    rpc_create_source,
    rpc_schedule_next_run,
    rpc_set_source_cadence,
    rpc_toggle_source,
    select_due_sources,
    select_sources,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/sources")
async def sources(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[SourceOut]]:
    rows = await select_sources(auth.access_token, str(org_id))
    return {"sources": [SourceOut.model_validate(row) for row in rows]}


@router.get("/sources/due")
async def due_sources(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[SourceOut]]:
    rows = await select_due_sources(auth.access_token, str(org_id))
    return {"sources": [SourceOut.model_validate(row) for row in rows]}


@router.post("/sources")
async def create_source(
    payload: SourceCreateIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, UUID]:
    source_id = await rpc_create_source(
        auth.access_token,
        {
            "p_org_id": str(payload.org_id),
            "p_name": payload.name,
            "p_type": payload.type,
            "p_url": payload.url,
        },
    )
    return {"id": UUID(source_id)}


@router.patch("/sources/{source_id}")
async def toggle_source(
    source_id: UUID, payload: SourceToggleIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    await rpc_toggle_source(
        auth.access_token,
        {"p_source_id": str(source_id), "p_is_enabled": payload.is_enabled},
    )
    return {"ok": True}


@router.patch("/sources/{source_id}/schedule")
async def schedule_source(
    source_id: UUID,
    payload: SourceScheduleIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, bool]:
    await rpc_set_source_cadence(
        auth.access_token,
        {"p_source_id": str(source_id), "p_cadence": payload.cadence},
    )
    await rpc_schedule_next_run(auth.access_token, {"p_source_id": str(source_id)})
    return {"ok": True}
