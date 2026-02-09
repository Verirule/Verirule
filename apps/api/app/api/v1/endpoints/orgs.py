from fastapi import APIRouter, Depends

from app.core.supabase_jwt import verify_supabase_jwt

router = APIRouter()
supabase_claims_dependency = Depends(verify_supabase_jwt)


@router.get("/orgs")
def orgs(_: dict[str, object] = supabase_claims_dependency) -> dict[str, list[object]]:
    return {"orgs": []}
