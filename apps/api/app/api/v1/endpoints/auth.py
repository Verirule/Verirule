from fastapi import APIRouter, Depends

from app.core.supabase_jwt import verify_supabase_jwt

router = APIRouter()
supabase_claims_dependency = Depends(verify_supabase_jwt)


@router.get("/me")
def me(claims: dict[str, object] = supabase_claims_dependency) -> dict[str, object]:
    safe_fields = ("sub", "email", "role", "iss", "exp")
    return {key: claims[key] for key in safe_fields if key in claims}
