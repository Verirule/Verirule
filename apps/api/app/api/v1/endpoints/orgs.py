from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.schemas.orgs import OrgCreateIn, OrgOut
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import supabase_rpc_create_org, supabase_select_orgs

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/orgs")
async def orgs(auth: VerifiedSupabaseAuth = supabase_auth_dependency) -> dict[str, list[OrgOut]]:
    rows = await supabase_select_orgs(auth.access_token)
    return {"orgs": [OrgOut.model_validate(row) for row in rows]}


@router.post("/orgs")
async def create_org(
    payload: OrgCreateIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, UUID]:
    org_id = await supabase_rpc_create_org(auth.access_token, payload.name)
    return {"id": UUID(org_id)}
