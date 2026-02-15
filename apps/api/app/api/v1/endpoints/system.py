import asyncio
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.schemas.system import (
    SystemHealthOut,
    SystemJobRowOut,
    SystemJobsListOut,
    SystemStatusListOut,
    SystemStatusRowOut,
)
from app.core.settings import get_settings
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    select_failed_audit_exports_service,
    select_failed_monitor_runs_service,
    select_failed_notification_jobs_service,
    select_org_ids_for_roles,
    select_system_status,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)
_SYSTEM_JOB_TYPES = {"notifications", "exports", "monitoring"}
SYSTEM_HEALTH_TIMEOUT_SECONDS = 1.5


def _claims_user_id(auth: VerifiedSupabaseAuth) -> str:
    sub = auth.claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return sub.strip()


@router.get("/system/status")
async def system_status(
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> SystemStatusListOut:
    rows = await select_system_status(auth.access_token)
    return SystemStatusListOut(status=[SystemStatusRowOut.model_validate(row) for row in rows])


@router.get("/system/health")
async def system_health(
) -> SystemHealthOut:
    settings = get_settings()
    supabase_ok = await _probe_supabase_health(
        supabase_url=settings.SUPABASE_URL,
        supabase_anon_key=settings.SUPABASE_ANON_KEY,
    )
    return SystemHealthOut(
        ok=True,
        version=settings.APP_VERSION.strip() or "dev",
        time_utc=datetime.now(UTC),
        supabase_ok=supabase_ok,
    )


async def _probe_supabase_health(*, supabase_url: str, supabase_anon_key: str) -> bool:
    url = f"{supabase_url.rstrip('/')}/auth/v1/health"
    headers = {
        "apikey": supabase_anon_key,
        "Authorization": f"Bearer {supabase_anon_key}",
        "Accept": "application/json",
    }
    timeout = httpx.Timeout(SYSTEM_HEALTH_TIMEOUT_SECONDS, connect=0.5)

    async def _request() -> bool:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            # Any non-5xx response indicates Supabase is reachable.
            return response.status_code < 500

    try:
        return await asyncio.wait_for(_request(), timeout=SYSTEM_HEALTH_TIMEOUT_SECONDS)
    except (TimeoutError, httpx.HTTPError):
        return False


@router.get("/system/jobs")
async def system_jobs(
    job_type: str | None = Query(default=None, alias="type"),
    status_value: str = Query(default="failed", alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> SystemJobsListOut:
    normalized_status = status_value.strip().lower()
    if normalized_status != "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only status=failed is supported.")

    normalized_type = (
        job_type.strip().lower() if isinstance(job_type, str) and job_type.strip() else None
    )
    if normalized_type is not None and normalized_type not in _SYSTEM_JOB_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid type. Expected notifications, exports, or monitoring.",
        )

    user_id = _claims_user_id(auth)
    admin_owner_org_ids = await select_org_ids_for_roles(auth.access_token, user_id, roles=("owner", "admin"))
    if not admin_owner_org_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    jobs: list[dict[str, object]] = []

    if normalized_type in {None, "notifications"}:
        rows = await select_failed_notification_jobs_service(org_ids=admin_owner_org_ids, limit=limit)
        for row in rows:
            jobs.append(
                {
                    "id": row.get("id"),
                    "org_id": row.get("org_id"),
                    "type": row.get("type") or "notification",
                    "status": row.get("status") or "failed",
                    "attempts": row.get("attempts") or 0,
                    "last_error": row.get("last_error"),
                    "updated_at": row.get("updated_at"),
                }
            )

    if normalized_type in {None, "exports"}:
        rows = await select_failed_audit_exports_service(org_ids=admin_owner_org_ids, limit=limit)
        for row in rows:
            jobs.append(
                {
                    "id": row.get("id"),
                    "org_id": row.get("org_id"),
                    "type": "export",
                    "status": row.get("status") or "failed",
                    "attempts": row.get("attempts") or 0,
                    "last_error": row.get("last_error"),
                    "updated_at": row.get("completed_at") or row.get("created_at"),
                }
            )

    if normalized_type in {None, "monitoring"}:
        rows = await select_failed_monitor_runs_service(org_ids=admin_owner_org_ids, limit=limit)
        for row in rows:
            jobs.append(
                {
                    "id": row.get("id"),
                    "org_id": row.get("org_id"),
                    "type": "monitoring",
                    "status": row.get("status") or "failed",
                    "attempts": row.get("attempts") or 0,
                    "last_error": row.get("last_error") or row.get("error"),
                    "updated_at": row.get("finished_at") or row.get("created_at"),
                }
            )

    def _updated_at_sort_key(value: dict[str, object]) -> tuple[int, str]:
        updated_at = value.get("updated_at")
        if isinstance(updated_at, str):
            return (0, updated_at)
        return (1, "")

    jobs.sort(key=_updated_at_sort_key, reverse=True)
    rows_out = [SystemJobRowOut.model_validate(row) for row in jobs[:limit]]
    return SystemJobsListOut(jobs=rows_out)
