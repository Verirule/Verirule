from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.schemas.readiness import OrgReadinessComputeOut, OrgReadinessSnapshotOut
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    get_latest_org_readiness,
    list_org_readiness,
    rpc_compute_org_readiness,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)
READINESS_LIMIT_QUERY = Query(default=30, ge=1, le=100)


@router.post("/orgs/{org_id}/readiness/compute")
async def compute_org_readiness(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> OrgReadinessComputeOut:
    snapshot_id = await rpc_compute_org_readiness(auth.access_token, str(org_id))
    latest = await get_latest_org_readiness(auth.access_token, str(org_id))
    if latest is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch readiness snapshot.",
        )
    return OrgReadinessComputeOut(
        snapshot_id=UUID(snapshot_id),
        readiness=OrgReadinessSnapshotOut.model_validate(latest),
    )


@router.get("/orgs/{org_id}/readiness")
async def list_readiness_snapshots(
    org_id: UUID,
    limit: int = READINESS_LIMIT_QUERY,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[OrgReadinessSnapshotOut]]:
    rows = await list_org_readiness(auth.access_token, str(org_id), limit=limit)
    return {"snapshots": [OrgReadinessSnapshotOut.model_validate(row) for row in rows]}


@router.get("/orgs/{org_id}/readiness/latest")
async def latest_readiness_snapshot(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> OrgReadinessSnapshotOut:
    row = await get_latest_org_readiness(auth.access_token, str(org_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Readiness snapshot not found.")
    return OrgReadinessSnapshotOut.model_validate(row)
