from fastapi import Depends, HTTPException, Request, status

from app.billing.entitlements import FeatureName, get_entitlements
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import select_org_billing, select_source_by_id

supabase_auth_dependency = Depends(verify_supabase_auth)


async def _resolve_org_id_from_request(request: Request, access_token: str) -> str:
    path_org_id = request.path_params.get("org_id")
    if isinstance(path_org_id, str) and path_org_id.strip():
        return path_org_id.strip()

    query_org_id = request.query_params.get("org_id")
    if query_org_id and query_org_id.strip():
        return query_org_id.strip()

    body_org_id: str | None = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            body_value = body.get("org_id")
            if isinstance(body_value, str) and body_value.strip():
                body_org_id = body_value.strip()
    except ValueError:
        body_org_id = None

    if body_org_id:
        return body_org_id

    source_id = request.path_params.get("source_id")
    if isinstance(source_id, str) and source_id.strip():
        source = await select_source_by_id(access_token, source_id.strip())
        source_org_id = source.get("org_id") if isinstance(source, dict) else None
        if isinstance(source_org_id, str) and source_org_id.strip():
            return source_org_id.strip()

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="org_id is required")


async def ensure_feature_enabled(
    *,
    access_token: str,
    org_id: str,
    feature_name: FeatureName,
) -> None:
    row = await select_org_billing(access_token, org_id)
    plan = row.get("plan") if isinstance(row, dict) else None
    entitlements = get_entitlements(plan if isinstance(plan, str) else None)
    if bool(getattr(entitlements, feature_name)):
        return

    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Upgrade required",
    )


def require_feature(feature_name: FeatureName):
    async def dependency(
        request: Request,
        auth: VerifiedSupabaseAuth = supabase_auth_dependency,
    ) -> None:
        org_id = await _resolve_org_id_from_request(request, auth.access_token)
        await ensure_feature_enabled(
            access_token=auth.access_token,
            org_id=org_id,
            feature_name=feature_name,
        )

    return Depends(dependency)
