from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends

from app.api.v1.schemas.system import SystemHealthOut, SystemStatusListOut, SystemStatusRowOut
from app.core.settings import get_settings
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import select_system_status

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/system/status")
async def system_status(
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> SystemStatusListOut:
    rows = await select_system_status(auth.access_token)
    return SystemStatusListOut(status=[SystemStatusRowOut.model_validate(row) for row in rows])


@router.get("/system/health")
async def system_health(
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> SystemHealthOut:
    settings = get_settings()
    rows = await select_system_status(auth.access_token)
    stale_after_seconds = max(1, settings.WORKER_STALE_AFTER_SECONDS)

    worker_row = next((row for row in rows if str(row.get("id") or "") == "worker"), None)
    worker_last_seen_at: datetime | None = None
    worker_status: Literal["ok", "stale", "unknown"] = "unknown"

    if worker_row:
        updated_at = worker_row.get("updated_at")
        if isinstance(updated_at, str):
            try:
                parsed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                worker_last_seen_at = parsed.astimezone(UTC)
            except ValueError:
                worker_last_seen_at = None
        elif isinstance(updated_at, datetime):
            worker_last_seen_at = (
                updated_at if updated_at.tzinfo is not None else updated_at.replace(tzinfo=UTC)
            ).astimezone(UTC)

    if worker_last_seen_at is not None:
        age_seconds = (datetime.now(UTC) - worker_last_seen_at).total_seconds()
        worker_status = "ok" if age_seconds <= stale_after_seconds else "stale"

    return SystemHealthOut(
        api="ok",
        worker=worker_status,
        worker_last_seen_at=worker_last_seen_at,
        stale_after_seconds=stale_after_seconds,
    )
