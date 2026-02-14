from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.exports import (
    ExportCreateIn,
    ExportCreateOut,
    ExportDownloadUrlOut,
    ExportOut,
)
from app.auth.roles import enforce_org_role
from app.billing.entitlements import get_entitlements
from app.billing.guard import ensure_feature_enabled, require_feature
from app.core.settings import get_settings
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    rpc_create_audit_export,
    select_audit_export_by_id,
    select_audit_exports,
    select_org_billing,
)
from app.core.supabase_storage_admin import create_signed_download_url

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


def _ensure_exports_configured() -> None:
    settings = get_settings()
    if not settings.SUPABASE_SERVICE_ROLE_KEY or not settings.SUPABASE_SERVICE_ROLE_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Audit exports are not configured.",
        )


def _parse_created_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


@router.post("/exports")
async def create_export(
    payload: ExportCreateIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
    _feature: None = require_feature("exports_enabled"),
) -> ExportCreateOut:
    await enforce_org_role(auth, str(payload.org_id), "member")
    _ensure_exports_configured()
    billing_row = await select_org_billing(auth.access_token, str(payload.org_id))
    raw_plan = billing_row.get("plan") if isinstance(billing_row, dict) else None
    entitlements = get_entitlements(raw_plan if isinstance(raw_plan, str) else None)

    if entitlements.max_exports_per_month is not None:
        existing_rows = await select_audit_exports(auth.access_token, str(payload.org_id))
        now = datetime.now(UTC)
        month_start = datetime(year=now.year, month=now.month, day=1, tzinfo=UTC)
        monthly_exports = 0
        for row in existing_rows:
            created_at = _parse_created_at(row.get("created_at"))
            if created_at is not None and created_at >= month_start:
                monthly_exports += 1

        if monthly_exports >= entitlements.max_exports_per_month:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Monthly export limit reached",
            )

    scope: dict[str, object] = {}
    if payload.from_ts:
        scope["from"] = payload.from_ts.isoformat()
    if payload.to:
        scope["to"] = payload.to.isoformat()
    if payload.include:
        scope["include"] = [item.strip() for item in payload.include if item.strip()]

    export_id = await rpc_create_audit_export(
        auth.access_token,
        {
            "p_org_id": str(payload.org_id),
            "p_format": payload.format,
            "p_scope": scope,
        },
    )
    return ExportCreateOut(id=UUID(export_id), status="queued")


@router.get("/exports")
async def list_exports(
    org_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
    _feature: None = require_feature("exports_enabled"),
) -> dict[str, list[ExportOut]]:
    await enforce_org_role(auth, str(org_id), "member")
    _ensure_exports_configured()
    rows = await select_audit_exports(auth.access_token, str(org_id))
    return {"exports": [ExportOut.model_validate(row) for row in rows]}


@router.get("/exports/{export_id}/download-url")
async def export_download_url(
    export_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> ExportDownloadUrlOut:
    _ensure_exports_configured()

    row = await select_audit_export_by_id(auth.access_token, str(export_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found.")
    org_id = row.get("org_id")
    if not isinstance(org_id, str) or not org_id.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid export response from Supabase.",
        )
    await enforce_org_role(auth, org_id, "member")
    await ensure_feature_enabled(
        access_token=auth.access_token,
        org_id=org_id,
        feature_name="exports_enabled",
    )

    export_status = str(row.get("status") or "")
    file_path = row.get("file_path")
    if export_status != "succeeded" or not isinstance(file_path, str) or not file_path.strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export is not ready for download.",
        )

    settings = get_settings()
    signed = await create_signed_download_url(
        settings.EXPORTS_BUCKET_NAME,
        file_path,
        settings.EXPORT_SIGNED_URL_SECONDS,
    )
    return ExportDownloadUrlOut(
        downloadUrl=signed["signed_url"],
        expiresIn=settings.EXPORT_SIGNED_URL_SECONDS,
    )
