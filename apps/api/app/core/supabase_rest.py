from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.settings import get_settings

AUDIT_PACKET_MAX_ROWS = 2_000


def supabase_rest_headers(access_token: str) -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {access_token}",
        "apikey": settings.SUPABASE_ANON_KEY,
        "Accept": "application/json",
    }


def supabase_public_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Accept": "application/json",
    }


def supabase_service_role_headers() -> dict[str, str]:
    settings = get_settings()
    service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not service_role_key or not service_role_key.strip():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Audit exports are not configured.",
        )
    return {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key,
        "Accept": "application/json",
    }


def _supabase_error_detail(response: httpx.Response) -> str | None:
    payload: Any
    try:
        payload = response.json()
    except ValueError:
        return None

    if not isinstance(payload, dict):
        return None

    detail = payload.get("message")
    if isinstance(detail, str) and detail:
        return detail

    detail = payload.get("detail")
    if isinstance(detail, str) and detail:
        return detail

    return None


async def _service_role_patch(
    table: str,
    row_id: str,
    payload: dict[str, Any],
    *,
    error_detail: str,
) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    params = {"id": f"eq.{row_id}"}
    headers = supabase_service_role_headers()
    headers["Prefer"] = "return=minimal"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(url, params=params, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error_detail) from exc


async def _service_role_upsert(
    table: str,
    payload: dict[str, Any],
    *,
    conflict_column: str,
    error_detail: str,
) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    headers = supabase_service_role_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params={"on_conflict": conflict_column},
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error_detail) from exc


async def supabase_select_orgs(access_token: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/orgs"
    params = {"select": "id,name,created_at"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch organizations from Supabase.",
        ) from exc

    payload = response.json()
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid organizations response from Supabase.",
        )

    for item in payload:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid organizations response from Supabase.",
            )

    return payload


async def select_org_member_role(access_token: str, org_id: str, user_id: str) -> str | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_members"
    params = {
        "select": "role",
        "org_id": f"eq.{org_id}",
        "user_id": f"eq.{user_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch organization membership from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid membership response from Supabase.")
    role = rows[0].get("role") if rows else None
    return role if isinstance(role, str) else None


async def select_org_members_service(org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_members"
    params = {
        "select": "org_id,user_id,role,created_at",
        "org_id": f"eq.{org_id}",
        "order": "created_at.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_service_role_headers())
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch organization members from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid organization members response from Supabase.")


async def select_org_member_service(org_id: str, user_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_members"
    params = {
        "select": "org_id,user_id,role,created_at",
        "org_id": f"eq.{org_id}",
        "user_id": f"eq.{user_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_service_role_headers())
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch organization member from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid organization member response from Supabase.")
    return rows[0] if rows else None


async def update_org_member_role_service(org_id: str, user_id: str, role: str) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_members"
    params = {
        "org_id": f"eq.{org_id}",
        "user_id": f"eq.{user_id}",
        "select": "org_id,user_id,role,created_at",
    }
    headers = supabase_service_role_headers()
    headers["Prefer"] = "return=representation"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(url, params=params, json={"role": role}, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update organization member role in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid organization member update response from Supabase.")
    updated = rows[0] if rows else None
    if not isinstance(updated, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization member not found.")
    return updated


async def delete_org_member_service(org_id: str, user_id: str) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_members"
    params = {"org_id": f"eq.{org_id}", "user_id": f"eq.{user_id}", "select": "user_id"}
    headers = supabase_service_role_headers()
    headers["Prefer"] = "return=representation"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url, params=params, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to remove organization member in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid organization member delete response from Supabase.")
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization member not found.")


async def count_org_members_by_role_service(org_id: str, role: str) -> int:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_members"
    params = {
        "select": "user_id",
        "org_id": f"eq.{org_id}",
        "role": f"eq.{role}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_service_role_headers())
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to count organization members in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid member count response from Supabase.")
    return len(rows)


async def select_org_invites(
    access_token: str,
    org_id: str,
    *,
    pending_only: bool = False,
) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_invites"
    params: dict[str, str] = {
        "select": "id,org_id,email,role,invited_by,expires_at,accepted_at,created_at",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
    }
    if pending_only:
        params["accepted_at"] = "is.null"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch organization invites from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid organization invites response from Supabase.")


async def select_org_invite_by_id(
    access_token: str,
    org_id: str,
    invite_id: str,
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_invites"
    params = {
        "select": "id,org_id,email,role,invited_by,expires_at,accepted_at,created_at",
        "org_id": f"eq.{org_id}",
        "id": f"eq.{invite_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch organization invite from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid organization invite response from Supabase.")
    return rows[0] if rows else None


async def delete_org_invite(access_token: str, org_id: str, invite_id: str) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_invites"
    params = {"org_id": f"eq.{org_id}", "id": f"eq.{invite_id}", "select": "id"}
    headers = supabase_rest_headers(access_token)
    headers["Prefer"] = "return=representation"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url, params=params, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to delete organization invite in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid organization invite delete response from Supabase.")
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.")


async def rpc_require_org_role(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/require_org_role"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Forbidden"
        detail_lower = error_detail.lower()
        if "insufficient org role" in detail_lower or "not a member of org" in detail_lower:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden") from exc
        if "not authenticated" in detail_lower:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to validate organization role in Supabase.",
        ) from exc


async def rpc_create_org_invite(access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/create_org_invite"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to create invite."
        detail_lower = error_detail.lower()
        if "insufficient org role" in detail_lower or "not a member of org" in detail_lower:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden") from exc
        if "not authenticated" in detail_lower:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create organization invite in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid create invite response from Supabase.")
    created = rows[0] if rows else None
    if not isinstance(created, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create invite response from Supabase.",
        )
    return created


async def rpc_accept_org_invite(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/accept_org_invite"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to accept invite."
        detail_lower = error_detail.lower()
        if "not authenticated" in detail_lower:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if "invalid or expired" in detail_lower:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to accept organization invite in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid accept invite response from Supabase.",
        )
    return response_payload


async def supabase_rpc_create_org(access_token: str, name: str) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/create_org"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={"p_name": name},
                headers=supabase_rest_headers(access_token),
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create organization in Supabase.",
        ) from exc

    payload = response.json()
    if not isinstance(payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create organization response from Supabase.",
        )

    return payload


READINESS_SELECT_COLUMNS = (
    "id,org_id,computed_at,score,controls_total,controls_with_evidence,evidence_items_total,"
    "evidence_items_done,open_alerts_high,open_tasks,overdue_tasks,metadata"
)


async def rpc_compute_org_readiness(access_token: str, org_id: str) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/compute_org_readiness"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                url,
                json={"p_org_id": org_id},
                headers=supabase_rest_headers(access_token),
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to compute organization readiness in Supabase.",
        ) from exc

    payload = response.json()
    if not isinstance(payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid compute readiness response from Supabase.",
        )
    return payload


async def list_org_readiness(access_token: str, org_id: str, limit: int = 30) -> list[dict[str, Any]]:
    bounded_limit = max(1, min(limit, 100))
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_readiness_snapshots"
    params = {
        "select": READINESS_SELECT_COLUMNS,
        "org_id": f"eq.{org_id}",
        "order": "computed_at.desc",
        "limit": str(bounded_limit),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch readiness snapshots from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid readiness snapshots response from Supabase.")


async def get_latest_org_readiness(access_token: str, org_id: str) -> dict[str, Any] | None:
    rows = await list_org_readiness(access_token, org_id, limit=1)
    return rows[0] if rows else None


async def select_sources(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/sources"
    params = {
        "select": "id,org_id,name,type,kind,config,title,url,is_enabled,cadence,next_run_at,last_run_at,created_at",
        "org_id": f"eq.{org_id}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch sources from Supabase.",
        ) from exc

    payload = response.json()
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid sources response from Supabase.",
        )

    for item in payload:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid sources response from Supabase.",
            )

    return payload


async def rpc_create_source(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/create_source_v2"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create source in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create source response from Supabase.",
        )

    return response_payload


async def rpc_toggle_source(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/toggle_source"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to toggle source in Supabase.",
        ) from exc


async def rpc_update_source(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/update_source"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update source in Supabase.",
        ) from exc


async def rpc_set_source_cadence(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/set_source_cadence"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update source cadence in Supabase.",
        ) from exc


async def rpc_schedule_next_run(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/schedule_next_run"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to schedule next source run in Supabase.",
        ) from exc


def _validated_list_payload(payload: Any, error_message: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_message,
        )

    for item in payload:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error_message,
            )

    return payload


def _with_time_range(
    params: dict[str, str],
    *,
    column: str,
    from_ts: str | None,
    to_ts: str | None,
) -> dict[str, str]:
    ranged = dict(params)
    if from_ts:
        ranged[column] = f"gte.{from_ts}"
    if to_ts:
        ranged[column] = f"lte.{to_ts}"
    return ranged


def _consume_audit_packet_rows(rows: list[dict[str, Any]], remaining: int) -> int:
    row_count = len(rows)
    if row_count > remaining:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Narrow your date range",
        )
    return remaining - row_count


async def select_monitor_runs(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/monitor_runs"
    params = {
        "select": "id,org_id,source_id,status,started_at,finished_at,error,created_at,attempts,next_attempt_at,last_error",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch monitor runs from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid monitor runs response from Supabase.")


async def select_queued_monitor_runs(access_token: str, limit: int = 5) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/monitor_runs"
    params = {
        "select": "id,org_id,source_id,status,attempts,next_attempt_at,last_error",
        "status": "eq.queued",
        "or": "(next_attempt_at.is.null,next_attempt_at.lte.now())",
        "order": "created_at.asc",
        "limit": str(limit),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch queued monitor runs from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid queued monitor runs response from Supabase.")


async def select_source_by_id(access_token: str, source_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/sources"
    params = {
        "select": "id,org_id,name,type,kind,config,title,url,is_enabled,cadence,next_run_at,last_run_at,etag,last_modified,content_type,tags",
        "id": f"eq.{source_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch source from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid source response from Supabase.")
    return rows[0] if rows else None


async def select_due_sources(access_token: str, org_id: str | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/sources"
    params = {
        "select": "id,org_id,name,type,kind,config,title,url,is_enabled,cadence,next_run_at,last_run_at,created_at",
        "cadence": "neq.manual",
        "is_enabled": "eq.true",
        "next_run_at": "lte.now()",
        "order": "next_run_at.asc",
    }
    if org_id:
        params["org_id"] = f"eq.{org_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch due sources from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid due sources response from Supabase.")


async def select_recent_active_monitor_runs_for_source(
    access_token: str,
    source_id: str,
    created_after_iso: str,
) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/monitor_runs"
    params = {
        "select": "id,source_id,status,created_at",
        "source_id": f"eq.{source_id}",
        "status": "in.(queued,running)",
        "created_at": f"gte.{created_after_iso}",
        "order": "created_at.desc",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch recent active monitor runs from Supabase.",
        ) from exc

    return _validated_list_payload(
        response.json(), "Invalid recent active monitor runs response from Supabase."
    )


async def select_latest_snapshot(access_token: str, source_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/snapshots"
    params = {
        "select": "id,org_id,source_id,run_id,fetched_url,content_hash,content_type,content_len,http_status,etag,last_modified,text_preview,text_fingerprint,canonical_title,canonical_text,item_id,item_published_at,fetched_at,created_at",
        "source_id": f"eq.{source_id}",
        "order": "created_at.desc",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch latest snapshot from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid latest snapshot response from Supabase.")
    return rows[0] if rows else None


async def select_latest_snapshot_for_run(access_token: str, run_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/snapshots"
    params = {
        "select": "id,run_id,canonical_title,item_published_at,created_at",
        "run_id": f"eq.{run_id}",
        "order": "created_at.desc",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch latest snapshot for run from Supabase.",
        ) from exc

    rows = _validated_list_payload(
        response.json(), "Invalid latest snapshot for run response from Supabase."
    )
    return rows[0] if rows else None


async def select_findings(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/findings"
    params = {
        "select": "id,org_id,source_id,run_id,title,summary,severity,detected_at,fingerprint,raw_url,raw_hash",
        "org_id": f"eq.{org_id}",
        "order": "detected_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch findings from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid findings response from Supabase.")


async def select_finding_explanations_by_org(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/finding_explanations"
    params = {
        "select": "finding_id",
        "org_id": f"eq.{org_id}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch finding explanations from Supabase.",
        ) from exc

    return _validated_list_payload(
        response.json(), "Invalid finding explanations response from Supabase."
    )


async def select_latest_finding_explanation(
    access_token: str, finding_id: str
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/finding_explanations"
    params = {
        "select": "id,org_id,finding_id,summary,diff_preview,citations,created_at",
        "finding_id": f"eq.{finding_id}",
        "order": "created_at.desc",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch finding explanation from Supabase.",
        ) from exc

    rows = _validated_list_payload(
        response.json(), "Invalid finding explanation response from Supabase."
    )
    return rows[0] if rows else None


async def select_alerts(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/alerts"
    params = {
        "select": "id,org_id,finding_id,task_id,status,owner_user_id,created_at,resolved_at",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch alerts from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid alerts response from Supabase.")


async def select_alert_by_id(access_token: str, alert_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/alerts"
    params = {
        "select": "id,org_id,finding_id,task_id,status,owner_user_id,created_at,resolved_at",
        "id": f"eq.{alert_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch alert from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid alert response from Supabase.")
    return rows[0] if rows else None


async def select_alert_by_id_for_org(
    access_token: str, org_id: str, alert_id: str
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/alerts"
    params = {
        "select": "id,org_id,finding_id,task_id,status,owner_user_id,created_at,resolved_at",
        "id": f"eq.{alert_id}",
        "org_id": f"eq.{org_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch alert from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid alert response from Supabase.")
    return rows[0] if rows else None


async def select_alerts_needing_tasks_service(limit: int = 50) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/alerts"
    params = {
        "select": "id,org_id,finding_id,task_id,status,created_at",
        "status": "eq.open",
        "task_id": "is.null",
        "order": "created_at.asc",
        "limit": str(limit),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_service_role_headers())
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch alerts needing tasks from Supabase.",
        ) from exc

    return _validated_list_payload(
        response.json(), "Invalid alerts needing tasks response from Supabase."
    )


async def list_active_org_ids_service(limit_per_table: int = 2000) -> list[str]:
    settings = get_settings()
    source_url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/sources"
    task_url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/tasks"
    params = {
        "select": "org_id",
        "limit": str(max(1, limit_per_table)),
    }
    headers = supabase_service_role_headers()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            sources_response = await client.get(source_url, params=params, headers=headers)
            sources_response.raise_for_status()
            tasks_response = await client.get(task_url, params=params, headers=headers)
            tasks_response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch active organizations from Supabase.",
        ) from exc

    source_rows = _validated_list_payload(
        sources_response.json(), "Invalid active organizations response from Supabase."
    )
    task_rows = _validated_list_payload(
        tasks_response.json(), "Invalid active organizations response from Supabase."
    )

    org_ids: set[str] = set()
    for row in [*source_rows, *task_rows]:
        org_id = row.get("org_id")
        if isinstance(org_id, str) and org_id.strip():
            org_ids.add(org_id.strip())

    return sorted(org_ids)


async def select_finding_by_id(access_token: str, finding_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/findings"
    params = {
        "select": "id,org_id,source_id,run_id,title,summary,severity,detected_at,fingerprint,raw_url,raw_hash",
        "id": f"eq.{finding_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch finding from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid finding response from Supabase.")
    return rows[0] if rows else None


async def select_audit_log(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/audit_events"
    params = {
        "select": "id,org_id,actor_user_id,actor_type,action,entity_type,entity_id,metadata,created_at",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch audit events from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid audit events response from Supabase.")


async def rpc_create_audit_export(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/create_audit_export"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to create audit export."
        normalized_detail = error_detail.lower()

        if "not authenticated" in normalized_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if "not a member of org" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail) from exc
        if exc.response.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create audit export.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create audit export.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create audit export response from Supabase.",
        )
    return response_payload


async def select_audit_exports(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/audit_exports"
    params = {
        "select": "id,org_id,requested_by_user_id,format,scope,status,file_path,file_sha256,error_text,created_at,completed_at,attempts,next_attempt_at,last_error",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch audit exports from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid audit exports response from Supabase.")


async def select_audit_export_by_id(access_token: str, export_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/audit_exports"
    params = {
        "select": "id,org_id,requested_by_user_id,format,scope,status,file_path,file_sha256,error_text,created_at,completed_at,attempts,next_attempt_at,last_error",
        "id": f"eq.{export_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch audit export from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid audit export response from Supabase.")
    return rows[0] if rows else None


async def select_queued_audit_exports_service(limit: int = 3) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/audit_exports"
    params = {
        "select": "id,org_id,requested_by_user_id,format,scope,status,created_at,attempts,next_attempt_at,last_error",
        "status": "eq.queued",
        "or": "(next_attempt_at.is.null,next_attempt_at.lte.now())",
        "order": "created_at.asc",
        "limit": str(limit),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_service_role_headers())
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch queued audit exports from Supabase.",
        ) from exc

    return _validated_list_payload(
        response.json(), "Invalid queued audit exports response from Supabase."
    )


async def select_audit_packet_data(
    access_token: str,
    org_id: str,
    from_ts: str | None,
    to_ts: str | None,
) -> dict[str, Any]:
    settings = get_settings()
    base_url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1"
    headers = supabase_rest_headers(access_token)
    remaining = AUDIT_PACKET_MAX_ROWS

    async def fetch_table(
        *,
        table: str,
        select: str,
        date_column: str,
        order: str,
    ) -> list[dict[str, Any]]:
        nonlocal remaining
        params = {
            "select": select,
            "org_id": f"eq.{org_id}",
            "order": order,
            "limit": str(remaining + 1),
        }
        params = _with_time_range(params, column=date_column, from_ts=from_ts, to_ts=to_ts)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{base_url}/{table}", params=params, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch export data from Supabase.",
            ) from exc

        rows = _validated_list_payload(response.json(), "Invalid export data response from Supabase.")
        remaining = _consume_audit_packet_rows(rows, remaining)
        return rows

    runs = await fetch_table(
        table="monitor_runs",
        select="id,org_id,source_id,status,started_at,finished_at,error,created_at",
        date_column="created_at",
        order="created_at.desc",
    )
    findings = await fetch_table(
        table="findings",
        select="id,org_id,source_id,run_id,title,summary,severity,detected_at,fingerprint,raw_url,raw_hash",
        date_column="detected_at",
        order="detected_at.desc",
    )
    explanations = await fetch_table(
        table="finding_explanations",
        select="finding_id",
        date_column="created_at",
        order="created_at.desc",
    )
    alerts = await fetch_table(
        table="alerts",
        select="id,org_id,finding_id,status,owner_user_id,created_at,resolved_at",
        date_column="created_at",
        order="created_at.desc",
    )
    tasks = await fetch_table(
        table="tasks",
        select="id,org_id,title,description,status,assignee_user_id,alert_id,finding_id,due_at,created_at,updated_at",
        date_column="created_at",
        order="created_at.desc",
    )
    task_evidence = await fetch_table(
        table="task_evidence",
        select="id,task_id,type,ref,created_at",
        date_column="created_at",
        order="created_at.asc",
    )
    evidence_files = await fetch_table(
        table="evidence_files",
        select="id,task_id,filename,storage_bucket,storage_path,content_type,byte_size,sha256,uploaded_by,created_at",
        date_column="created_at",
        order="created_at.asc",
    )
    task_comments = await fetch_table(
        table="task_comments",
        select="id,task_id,author_user_id,body,created_at",
        date_column="created_at",
        order="created_at.asc",
    )
    snapshots = await fetch_table(
        table="snapshots",
        select="id,org_id,source_id,run_id,http_status,content_type,content_len,fetched_at",
        date_column="fetched_at",
        order="fetched_at.desc",
    )
    audit_timeline = await fetch_table(
        table="audit_events",
        select="id,org_id,actor_user_id,actor_type,action,entity_type,entity_id,metadata,created_at",
        date_column="created_at",
        order="created_at.desc",
    )
    readiness_summary: dict[str, Any] | None = None
    readiness_params = {
        "select": READINESS_SELECT_COLUMNS,
        "org_id": f"eq.{org_id}",
        "order": "computed_at.desc",
        "limit": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            readiness_response = await client.get(
                f"{base_url}/org_readiness_snapshots",
                params=readiness_params,
                headers=headers,
            )
            readiness_response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch export data from Supabase.",
        ) from exc
    readiness_rows = _validated_list_payload(
        readiness_response.json(), "Invalid export data response from Supabase."
    )
    if readiness_rows:
        readiness_summary = readiness_rows[0]

    return {
        "org_id": org_id,
        "from": from_ts,
        "to": to_ts,
        "runs": runs,
        "findings": findings,
        "finding_explanations": explanations,
        "alerts": alerts,
        "tasks": tasks,
        "task_evidence": task_evidence,
        "evidence_files": evidence_files,
        "task_comments": task_comments,
        "snapshots": snapshots,
        "audit_timeline": audit_timeline,
        "readiness_summary": readiness_summary,
        "row_count": AUDIT_PACKET_MAX_ROWS - remaining,
    }


async def update_audit_export_status(
    export_id: str,
    status_value: str,
    file_path: str | None,
    file_sha256: str | None,
    error_text: str | None,
    completed_at: str | None,
) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/audit_exports"
    params = {"id": f"eq.{export_id}"}
    payload = {
        "status": status_value,
        "file_path": file_path,
        "file_sha256": file_sha256,
        "error_text": error_text,
        "completed_at": completed_at,
    }
    headers = supabase_service_role_headers()
    headers["Prefer"] = "return=minimal"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(url, params=params, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update audit export status in Supabase.",
        ) from exc


async def mark_audit_export_attempt_started(export_id: str, attempts: int) -> None:
    await _service_role_patch(
        "audit_exports",
        export_id,
        {
            "status": "running",
            "attempts": attempts,
            "next_attempt_at": None,
            "last_error": None,
            "error_text": None,
            "completed_at": None,
        },
        error_detail="Failed to mark audit export as running.",
    )


async def mark_audit_export_for_retry(
    export_id: str,
    attempts: int,
    next_attempt_at: str,
    last_error: str,
) -> None:
    await _service_role_patch(
        "audit_exports",
        export_id,
        {
            "status": "queued",
            "attempts": attempts,
            "next_attempt_at": next_attempt_at,
            "last_error": last_error,
            "error_text": last_error,
            "completed_at": None,
        },
        error_detail="Failed to schedule audit export retry.",
    )


async def mark_audit_export_dead_letter(
    export_id: str,
    attempts: int,
    last_error: str,
    completed_at: str,
) -> None:
    await _service_role_patch(
        "audit_exports",
        export_id,
        {
            "status": "failed",
            "attempts": attempts,
            "next_attempt_at": None,
            "last_error": last_error,
            "error_text": last_error,
            "completed_at": completed_at,
        },
        error_detail="Failed to mark audit export as failed.",
    )


async def mark_monitor_run_attempt_started(run_id: str, attempts: int) -> None:
    await _service_role_patch(
        "monitor_runs",
        run_id,
        {
            "attempts": attempts,
            "next_attempt_at": None,
            "last_error": None,
            "error": None,
        },
        error_detail="Failed to mark monitor run as running.",
    )


async def clear_monitor_run_error_state(run_id: str) -> None:
    await _service_role_patch(
        "monitor_runs",
        run_id,
        {
            "next_attempt_at": None,
            "last_error": None,
            "error": None,
        },
        error_detail="Failed to clear monitor run retry fields.",
    )


async def mark_monitor_run_for_retry(
    run_id: str,
    attempts: int,
    next_attempt_at: str,
    last_error: str,
) -> None:
    await _service_role_patch(
        "monitor_runs",
        run_id,
        {
            "status": "queued",
            "attempts": attempts,
            "next_attempt_at": next_attempt_at,
            "last_error": last_error,
            "error": None,
            "finished_at": None,
        },
        error_detail="Failed to schedule monitor run retry.",
    )


async def mark_monitor_run_dead_letter(
    run_id: str,
    attempts: int,
    last_error: str,
    failed_at: str,
) -> None:
    await _service_role_patch(
        "monitor_runs",
        run_id,
        {
            "status": "failed",
            "attempts": attempts,
            "next_attempt_at": None,
            "last_error": last_error,
            "error": last_error,
            "finished_at": failed_at,
        },
        error_detail="Failed to mark monitor run as failed.",
    )


async def upsert_system_status(status_id: str, payload: dict[str, Any]) -> None:
    await _service_role_upsert(
        "system_status",
        {
            "id": status_id,
            "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "payload": payload,
        },
        conflict_column="id",
        error_detail="Failed to upsert system status.",
    )


async def select_system_status(access_token: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/system_status"
    params = {
        "select": "id,updated_at,payload",
        "order": "id.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch system status from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid system status response from Supabase.")


async def rpc_create_monitor_run(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/create_monitor_run"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create monitor run in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create monitor run response from Supabase.",
        )

    return response_payload


async def rpc_set_monitor_run_state(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/set_monitor_run_state"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update monitor run state in Supabase.",
        ) from exc


async def rpc_insert_snapshot(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/insert_snapshot"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to insert snapshot in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid insert snapshot response from Supabase.",
        )

    return response_payload


async def rpc_insert_snapshot_v2(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/insert_snapshot_v2"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to insert snapshot in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid insert snapshot response from Supabase.",
        )

    return response_payload


async def rpc_insert_snapshot_v3(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/insert_snapshot_v3"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to insert snapshot in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid insert snapshot response from Supabase.",
        )

    return response_payload


async def rpc_upsert_finding(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/upsert_finding"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upsert finding in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid upsert finding response from Supabase.",
        )

    return response_payload


async def rpc_set_alert_status(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/set_alert_status"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update alert in Supabase.",
        ) from exc


async def rpc_record_audit_event(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/record_audit_event"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to write audit event in Supabase.",
        ) from exc


async def rpc_append_audit(access_token: str, payload: dict[str, Any]) -> None:
    await rpc_record_audit_event(access_token, payload)


async def rpc_insert_finding_explanation(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/insert_finding_explanation"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to insert finding explanation in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid finding explanation response from Supabase.",
        )

    return response_payload


async def rpc_set_source_fetch_metadata(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/set_source_fetch_metadata"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update source fetch metadata in Supabase.",
        ) from exc


async def select_tasks(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/tasks"
    params = {
        "select": "id,org_id,title,description,status,assignee_user_id,alert_id,finding_id,due_at,created_at,updated_at",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch tasks from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid tasks response from Supabase.")


async def select_task_by_id(access_token: str, task_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/tasks"
    params = {
        "select": "id,org_id",
        "id": f"eq.{task_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch task from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid task response from Supabase.")
    return rows[0] if rows else None


async def select_tasks_for_alert(access_token: str, alert_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/tasks"
    params = {
        "select": "id,org_id",
        "alert_id": f"eq.{alert_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch alert tasks from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid alert tasks response from Supabase.")


async def select_task_comments(access_token: str, task_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/task_comments"
    params = {
        "select": "id,task_id,author_user_id,body,created_at",
        "task_id": f"eq.{task_id}",
        "order": "created_at.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch task comments from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid task comments response from Supabase.")


async def select_task_evidence(access_token: str, task_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/task_evidence"
    params = {
        "select": "id,task_id,type,ref,created_at",
        "task_id": f"eq.{task_id}",
        "order": "created_at.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch task evidence from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid task evidence response from Supabase.")


async def select_task_evidence_by_id(
    access_token: str, task_id: str, evidence_id: str
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/task_evidence"
    params = {
        "select": "id,task_id,type,ref",
        "id": f"eq.{evidence_id}",
        "task_id": f"eq.{task_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch evidence from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid evidence response from Supabase.")
    return rows[0] if rows else None


async def select_evidence_files_by_task(
    access_token: str, task_id: str, org_id: str
) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/evidence_files"
    params = {
        "select": "id,org_id,task_id,filename,storage_bucket,storage_path,content_type,byte_size,sha256,uploaded_by,created_at",
        "task_id": f"eq.{task_id}",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch evidence files from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid evidence files response from Supabase.")


async def select_evidence_file_by_id(
    access_token: str, evidence_file_id: str, org_id: str
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/evidence_files"
    params = {
        "select": "id,org_id,task_id,filename,storage_bucket,storage_path,content_type,byte_size,sha256,uploaded_by,created_at",
        "id": f"eq.{evidence_file_id}",
        "org_id": f"eq.{org_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch evidence file from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid evidence file response from Supabase.")
    return rows[0] if rows else None


async def insert_evidence_file(access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/evidence_files"
    headers = supabase_rest_headers(access_token)
    headers["Prefer"] = "return=representation"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create evidence file metadata in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid evidence file create response from Supabase.")
    created = rows[0] if rows else None
    if not isinstance(created, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid evidence file create response from Supabase.",
        )
    return created


async def update_evidence_file_finalize_service(
    evidence_file_id: str, org_id: str, sha256: str, uploaded_by: str
) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/evidence_files"
    params = {"id": f"eq.{evidence_file_id}", "org_id": f"eq.{org_id}"}
    headers = supabase_service_role_headers()
    headers["Prefer"] = "return=representation"
    payload = {"sha256": sha256, "uploaded_by": uploaded_by}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(url, params=params, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to finalize evidence file in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid evidence finalize response from Supabase.")
    updated = rows[0] if rows else None
    if not isinstance(updated, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")
    return updated


async def delete_evidence_file(access_token: str, evidence_file_id: str, org_id: str) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/evidence_files"
    params = {"id": f"eq.{evidence_file_id}", "org_id": f"eq.{org_id}"}
    headers = supabase_rest_headers(access_token)
    headers["Prefer"] = "return=minimal"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url, params=params, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to delete evidence file metadata in Supabase.",
        ) from exc


async def rpc_create_task(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/create_task"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create task in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create task response from Supabase.",
        )

    return response_payload


async def insert_task_service(
    org_id: str,
    *,
    title: str,
    description: str | None,
    alert_id: str | None,
    finding_id: str | None,
) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/tasks"
    headers = supabase_service_role_headers()
    headers["Prefer"] = "return=representation"
    payload = {
        "org_id": org_id,
        "title": title,
        "description": description,
        "status": "open",
        "assignee_user_id": None,
        "alert_id": alert_id,
        "finding_id": finding_id,
        "due_at": None,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create task in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid create task response from Supabase.")
    created_task = rows[0] if rows else None
    task_id = created_task.get("id") if isinstance(created_task, dict) else None
    if not isinstance(task_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create task response from Supabase.",
        )
    return task_id


async def bulk_insert_task_controls(
    access_token: str,
    org_id: str,
    task_id: str,
    control_ids: list[str],
) -> int:
    normalized_ids = [control_id.strip() for control_id in control_ids if control_id.strip()]
    if not normalized_ids:
        return 0

    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/task_controls"
    headers = supabase_rest_headers(access_token)
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    payload = [{"org_id": org_id, "task_id": task_id, "control_id": control_id} for control_id in normalized_ids]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params={"on_conflict": "org_id,task_id,control_id"},
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to map controls to task in Supabase.",
        ) from exc

    return len(normalized_ids)


async def bulk_insert_task_controls_service(
    org_id: str,
    task_id: str,
    control_ids: list[str],
) -> int:
    normalized_ids = [control_id.strip() for control_id in control_ids if control_id.strip()]
    if not normalized_ids:
        return 0

    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/task_controls"
    headers = supabase_service_role_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    payload = [{"org_id": org_id, "task_id": task_id, "control_id": control_id} for control_id in normalized_ids]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                params={"on_conflict": "org_id,task_id,control_id"},
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to map controls to task in Supabase.",
        ) from exc

    return len(normalized_ids)


async def bulk_insert_task_evidence_service(
    org_id: str,
    task_id: str,
    evidence_items: list[dict[str, str]],
) -> int:
    normalized_items = [
        item
        for item in evidence_items
        if isinstance(item, dict)
        and isinstance(item.get("type"), str)
        and item.get("type")
        and isinstance(item.get("ref"), str)
        and item.get("ref")
    ]
    if not normalized_items:
        return 0

    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/task_evidence"
    headers = supabase_service_role_headers()
    headers["Prefer"] = "return=minimal"
    payload = [
        {
            "org_id": org_id,
            "task_id": task_id,
            "type": str(item["type"]),
            "ref": str(item["ref"]),
        }
        for item in normalized_items
    ]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to add task evidence in Supabase.",
        ) from exc

    return len(normalized_items)


async def rpc_link_alert_task(access_token: str, org_id: str, alert_id: str, task_id: str) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/link_alert_task"
    payload = {
        "p_org_id": org_id,
        "p_alert_id": alert_id,
        "p_task_id": task_id,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to link alert task in Supabase."
        normalized_detail = error_detail.lower()
        if "not authenticated" in normalized_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if "not a member of org" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail) from exc
        if "alert not found" in normalized_detail or "task not found" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_detail) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to link alert task in Supabase.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to link alert task in Supabase.",
        ) from exc


async def update_alert_task_id(access_token: str, org_id: str, alert_id: str, task_id: str) -> None:
    await rpc_link_alert_task(access_token, org_id, alert_id, task_id)


async def rpc_set_task_status(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/set_task_status"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to set task status in Supabase.",
        ) from exc


async def rpc_add_task_comment(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/add_task_comment"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to add task comment in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid add task comment response from Supabase.",
        )

    return response_payload


async def rpc_add_task_evidence(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/add_task_evidence"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to add task evidence in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid add task evidence response from Supabase.",
        )

    return response_payload


async def select_integrations(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/integrations"
    params = {
        "select": "id,org_id,type,status,config,updated_at",
        "org_id": f"eq.{org_id}",
        "order": "type.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch integrations from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid integrations response from Supabase.")


async def select_integration(access_token: str, org_id: str, integration_type: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/integrations"
    params = {
        "select": "id,org_id,type,status,config,updated_at",
        "org_id": f"eq.{org_id}",
        "type": f"eq.{integration_type}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch integration from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid integration response from Supabase.")
    return rows[0] if rows else None


async def rpc_upsert_integration(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/upsert_integration"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upsert integration in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid upsert integration response from Supabase.",
        )

    return response_payload


async def rpc_disable_integration(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/disable_integration"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to disable integration in Supabase.",
        ) from exc


async def select_integration_secret(
    access_token: str, org_id: str, integration_type: str
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/integrations"
    params = {
        "select": "id,org_id,type,status,config,secret_ciphertext,updated_at",
        "org_id": f"eq.{org_id}",
        "type": f"eq.{integration_type}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch integration secret from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid integration secret response from Supabase.")
    return rows[0] if rows else None


async def select_org_billing(access_token: str, org_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/orgs"
    params = {
        "select": "id,stripe_customer_id,stripe_subscription_id,plan,plan_status,current_period_end",
        "id": f"eq.{org_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch billing state from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid billing response from Supabase.")
    return rows[0] if rows else None


async def ensure_alert_task_rules(access_token: str, org_id: str) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/ensure_alert_task_rules"
    payload = {"p_org_id": org_id}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to initialize alert task rules."
        normalized_detail = error_detail.lower()
        if "not authenticated" in normalized_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if "not a member of org" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to initialize alert task rules.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to initialize alert task rules.",
        ) from exc


async def get_alert_task_rules(access_token: str, org_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/alert_task_rules"
    params = {
        "select": "org_id,enabled,auto_create_task_on_alert,min_severity,auto_link_suggested_controls,auto_add_evidence_checklist,created_at,updated_at",
        "org_id": f"eq.{org_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch automation rules from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid automation rules response from Supabase.")
    return rows[0] if rows else None


async def update_alert_task_rules(
    access_token: str, org_id: str, patch: dict[str, Any]
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/alert_task_rules"
    params = {
        "org_id": f"eq.{org_id}",
        "select": "org_id,enabled,auto_create_task_on_alert,min_severity,auto_link_suggested_controls,auto_add_evidence_checklist,created_at,updated_at",
    }
    headers = supabase_rest_headers(access_token)
    headers["Prefer"] = "return=representation"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(url, params=params, json=patch, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update automation rules in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid automation rules response from Supabase.")
    return rows[0] if rows else None


async def select_billing_events(
    access_token: str, org_id: str, *, limit: int = 25
) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/billing_events"
    params = {
        "select": "id,org_id,stripe_event_id,event_type,created_at,processed_at,status,error",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
        "limit": str(limit),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch billing events from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid billing events response from Supabase.")


async def rpc_upsert_alert_for_finding(access_token: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/upsert_alert_for_finding"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upsert alert in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid upsert alert response from Supabase.",
        )
    if not isinstance(response_payload.get("id"), str) or not isinstance(response_payload.get("created"), bool):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid upsert alert response from Supabase.",
        )

    return response_payload


async def list_framework_templates(access_token: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/framework_templates"
    params = {
        "select": "id,slug,name,description,category,is_public,created_at",
        "is_public": "eq.true",
        "order": "name.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch framework templates from Supabase.",
        ) from exc

    return _validated_list_payload(
        response.json(), "Invalid framework templates response from Supabase."
    )


async def get_framework_template_by_slug(
    access_token: str, slug: str
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/framework_templates"
    params = {
        "select": "id,slug,name,description,category,is_public,created_at",
        "is_public": "eq.true",
        "slug": f"eq.{slug}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch framework template from Supabase.",
        ) from exc

    rows = _validated_list_payload(
        response.json(), "Invalid framework template response from Supabase."
    )
    return rows[0] if rows else None


async def list_framework_template_sources(
    access_token: str, template_id: str | None = None
) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/framework_template_sources"
    params = {
        "select": "id,template_id,title,url,kind,cadence,tags,enabled_by_default,created_at",
        "order": "title.asc",
    }
    if template_id:
        params["template_id"] = f"eq.{template_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch framework template sources from Supabase.",
        ) from exc

    return _validated_list_payload(
        response.json(), "Invalid framework template sources response from Supabase."
    )


async def rpc_create_source_v3(access_token: str, payload: dict[str, Any]) -> str:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/create_source_v3"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to create source in Supabase."
        normalized_detail = error_detail.lower()
        if "not authenticated" in normalized_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if "not a member of org" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail) from exc
        if exc.response.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create source in Supabase.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create source in Supabase.",
        ) from exc

    response_payload = response.json()
    if not isinstance(response_payload, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid create source response from Supabase.",
        )
    return response_payload


async def list_sources_by_org(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/sources"
    params = {
        "select": "id,org_id,name,title,url,kind,cadence,is_enabled,tags",
        "org_id": f"eq.{org_id}",
        "order": "created_at.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch sources from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid sources response from Supabase.")


async def insert_sources_bulk(
    access_token: str, org_id: str, sources: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    inserted: list[dict[str, Any]] = []
    for source in sources:
        source_id = await rpc_create_source_v3(
            access_token,
            {
                "p_org_id": org_id,
                "p_name": source.get("name"),
                "p_url": source.get("url"),
                "p_kind": source.get("kind"),
                "p_cadence": source.get("cadence"),
                "p_tags": source.get("tags") or [],
                "p_is_enabled": source.get("is_enabled"),
                "p_title": source.get("title"),
                "p_config": source.get("config") or {},
            },
        )
        inserted.append(
            {
                "id": source_id,
                "name": source.get("name"),
                "title": source.get("title"),
                "url": source.get("url"),
                "kind": source.get("kind"),
                "cadence": source.get("cadence"),
                "is_enabled": source.get("is_enabled"),
                "tags": source.get("tags") or [],
            }
        )
    return inserted


def _in_filter(values: list[str]) -> str:
    normalized = [value.strip() for value in values if value.strip()]
    return f"in.({','.join(normalized)})"


async def list_controls(access_token: str, framework_slug: str | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/controls"
    params = {
        "select": "id,framework_slug,control_key,title,description,severity_default,tags,created_at",
        "order": "framework_slug.asc,control_key.asc",
    }
    if framework_slug:
        params["framework_slug"] = f"eq.{framework_slug}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch controls from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid controls response from Supabase.")


async def list_controls_by_ids(access_token: str, control_ids: list[str]) -> list[dict[str, Any]]:
    normalized_ids = [control_id.strip() for control_id in control_ids if control_id.strip()]
    if not normalized_ids:
        return []

    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/controls"
    params = {
        "select": "id,framework_slug,control_key,title,description,severity_default,tags,created_at",
        "id": _in_filter(normalized_ids),
        "order": "framework_slug.asc,control_key.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch controls from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid controls response from Supabase.")


async def get_control_by_id(access_token: str, control_id: str) -> dict[str, Any] | None:
    rows = await list_controls_by_ids(access_token, [control_id])
    return rows[0] if rows else None


async def list_control_evidence(access_token: str, control_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/control_evidence_items"
    params = {
        "select": "id,control_id,label,description,evidence_type,required,sort_order,created_at",
        "control_id": f"eq.{control_id}",
        "order": "sort_order.asc,label.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch control evidence from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid control evidence response from Supabase.")


async def list_control_evidence_for_controls(
    access_token: str, control_ids: list[str]
) -> list[dict[str, Any]]:
    normalized_ids = [control_id.strip() for control_id in control_ids if control_id.strip()]
    if not normalized_ids:
        return []

    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/control_evidence_items"
    params = {
        "select": "id,control_id,label,description,evidence_type,required,sort_order,created_at",
        "control_id": _in_filter(normalized_ids),
        "order": "control_id.asc,sort_order.asc,label.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch control evidence from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid control evidence response from Supabase.")


async def list_control_evidence_items(
    access_token: str, control_ids: list[str]
) -> list[dict[str, Any]]:
    return await list_control_evidence_for_controls(access_token, control_ids)


async def get_control_guidance(access_token: str, control_id: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/control_guidance"
    params = {
        "select": "id,control_id,guidance_markdown,created_at",
        "control_id": f"eq.{control_id}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch control guidance from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid control guidance response from Supabase.")
    return rows[0] if rows else None


async def list_org_controls(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_controls"
    params = {
        "select": "id,org_id,control_id,status,owner_user_id,notes,created_at",
        "org_id": f"eq.{org_id}",
        "order": "created_at.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch org controls from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid org controls response from Supabase.")


async def patch_org_control_status(
    access_token: str,
    org_control_id: str,
    status_value: str,
    owner_user_id: str | None = None,
    notes: str | None = None,
    *,
    include_owner_user_id: bool = False,
    include_notes: bool = False,
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_controls"
    params = {
        "id": f"eq.{org_control_id}",
        "select": "id,org_id,control_id,status,owner_user_id,notes,created_at",
    }
    headers = supabase_rest_headers(access_token)
    headers["Prefer"] = "return=representation"
    payload: dict[str, Any] = {"status": status_value}
    if include_owner_user_id:
        payload["owner_user_id"] = owner_user_id
    if include_notes:
        payload["notes"] = notes

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(url, params=params, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to update org control in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid org control update response from Supabase.")
    return rows[0] if rows else None


async def rpc_install_controls_for_template(
    access_token: str, org_id: str, template_slug: str
) -> int:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/install_controls_for_template"
    payload = {
        "p_org_id": org_id,
        "p_template_slug": template_slug,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to install controls in Supabase."
        normalized_detail = error_detail.lower()
        if "not authenticated" in normalized_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if "not a member of org" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail) from exc
        if "template not found" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_detail) from exc
        if exc.response.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to install controls in Supabase.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to install controls in Supabase.",
        ) from exc

    response_payload = response.json()
    if isinstance(response_payload, bool):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid install controls response from Supabase.",
        )
    if isinstance(response_payload, int):
        return response_payload
    if isinstance(response_payload, float) and response_payload.is_integer():
        return int(response_payload)
    if isinstance(response_payload, str):
        try:
            return int(response_payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid install controls response from Supabase.",
            ) from exc
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Invalid install controls response from Supabase.",
    )


async def list_finding_controls(access_token: str, org_id: str, finding_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/finding_controls"
    params = {
        "select": "id,org_id,finding_id,control_id,confidence,created_at",
        "org_id": f"eq.{org_id}",
        "finding_id": f"eq.{finding_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch finding control mappings from Supabase.",
        ) from exc

    return _validated_list_payload(
        response.json(), "Invalid finding control mappings response from Supabase."
    )


async def list_finding_controls_by_org(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/finding_controls"
    params = {
        "select": "id,org_id,finding_id,control_id,confidence,created_at",
        "org_id": f"eq.{org_id}",
        "order": "created_at.desc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch finding control mappings from Supabase.",
        ) from exc

    return _validated_list_payload(
        response.json(), "Invalid finding control mappings response from Supabase."
    )


async def rpc_link_finding_to_control(
    access_token: str, org_id: str, finding_id: str, control_id: str, confidence: str
) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/link_finding_to_control"
    payload = {
        "p_org_id": org_id,
        "p_finding_id": finding_id,
        "p_control_id": control_id,
        "p_confidence": confidence,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to link finding to control in Supabase."
        normalized_detail = error_detail.lower()
        if "not authenticated" in normalized_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if "not a member of org" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail) from exc
        if "not found" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_detail) from exc
        if exc.response.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to link finding to control in Supabase.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to link finding to control in Supabase.",
        ) from exc


async def select_templates_public() -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/templates"
    params = {
        "select": "id,slug,name,description,default_cadence,tags,created_at",
        "order": "name.asc",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_public_headers())
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch templates from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid templates response from Supabase.")


async def select_template_by_slug_public(slug: str) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/templates"
    params = {
        "select": "id,slug,name,description,default_cadence,tags,created_at",
        "slug": f"eq.{slug}",
        "limit": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_public_headers())
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch template from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid template response from Supabase.")
    return rows[0] if rows else None


async def select_template_sources_public(template_id: str | None = None) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/template_sources"
    params = {
        "select": "id,template_id,name,url,cadence,tags,created_at",
        "order": "name.asc",
    }
    if template_id:
        params["template_id"] = f"eq.{template_id}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_public_headers())
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch template sources from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid template sources response from Supabase.")


async def rpc_install_template(access_token: str, payload: dict[str, Any]) -> int:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/install_template"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        error_detail = _supabase_error_detail(exc.response) or "Failed to install template in Supabase."
        normalized_detail = error_detail.lower()

        if "not authenticated" in normalized_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if "not a member of org" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail) from exc
        if "template not found" in normalized_detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_detail) from exc
        if exc.response.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to install template in Supabase.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to install template in Supabase.",
        ) from exc

    response_payload = response.json()
    if isinstance(response_payload, bool):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid install template response from Supabase.",
        )
    if isinstance(response_payload, int):
        return response_payload
    if isinstance(response_payload, float) and response_payload.is_integer():
        return int(response_payload)
    if isinstance(response_payload, str):
        try:
            return int(response_payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid install template response from Supabase.",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Invalid install template response from Supabase.",
    )
