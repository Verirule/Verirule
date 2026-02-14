import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.v1.schemas.orgs import OrgCreateIn, OrgOut
from app.core.logging import get_logger
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import supabase_rpc_create_org, supabase_select_orgs

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)
logger = get_logger("api.orgs")
ORG_CREATE_TIMEOUT_SECONDS = 10.0


def _normalize_org_name(name: str) -> str:
    return name.strip()


def _find_existing_org_id(rows: list[dict[str, object]], normalized_name: str) -> str | None:
    target_name = normalized_name.casefold()
    for row in rows:
        row_name = row.get("name")
        row_id = row.get("id")
        if not isinstance(row_name, str) or not isinstance(row_id, str):
            continue
        if row_name.strip().casefold() == target_name:
            return row_id
    return None


def _request_id_from_state(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) and value.strip() else None


def _user_id_from_claims(auth: VerifiedSupabaseAuth) -> str | None:
    value = auth.claims.get("sub")
    return value if isinstance(value, str) and value.strip() else None


async def _create_org_idempotent(access_token: str, normalized_name: str) -> str:
    rows = await supabase_select_orgs(access_token)
    existing_org_id = _find_existing_org_id(rows, normalized_name)
    if existing_org_id is not None:
        return existing_org_id

    return await supabase_rpc_create_org(access_token, normalized_name)


@router.get("/orgs")
async def orgs(auth: VerifiedSupabaseAuth = supabase_auth_dependency) -> dict[str, list[OrgOut]]:
    rows = await supabase_select_orgs(auth.access_token)
    return {"orgs": [OrgOut.model_validate(row) for row in rows]}


@router.get("/orgs/mine")
async def my_orgs(auth: VerifiedSupabaseAuth = supabase_auth_dependency) -> dict[str, list[OrgOut]]:
    rows = await supabase_select_orgs(auth.access_token)
    return {"orgs": [OrgOut.model_validate(row) for row in rows]}


@router.post("/orgs")
async def create_org(
    payload: OrgCreateIn,
    request: Request,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, UUID]:
    normalized_name = _normalize_org_name(payload.name)
    if len(normalized_name) < 2 or len(normalized_name) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workspace name must be between 2 and 64 characters.",
        )

    request_id = _request_id_from_state(request)
    user_id = _user_id_from_claims(auth)

    try:
        org_id = await asyncio.wait_for(
            _create_org_idempotent(auth.access_token, normalized_name),
            timeout=ORG_CREATE_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        logger.warning(
            "Workspace creation timed out.",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "org_name": normalized_name,
                "status_code": status.HTTP_504_GATEWAY_TIMEOUT,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Workspace creation timed out. Please try again.",
        ) from exc
    except HTTPException as exc:
        message = exc.detail if isinstance(exc.detail, str) else "Workspace creation failed."
        logger.warning(
            message,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "org_name": normalized_name,
                "status_code": exc.status_code,
            },
        )
        raise
    except Exception as exc:
        logger.error(
            "Workspace creation failed.",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "org_name": normalized_name,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workspace creation failed.",
        ) from exc

    return {"id": UUID(org_id)}
