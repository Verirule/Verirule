from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.settings import get_settings


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


async def select_sources(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/sources"
    params = {
        "select": "id,org_id,name,type,url,is_enabled,cadence,next_run_at,last_run_at,created_at",
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
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/create_source"

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


async def select_monitor_runs(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/monitor_runs"
    params = {
        "select": "id,org_id,source_id,status,started_at,finished_at,error,created_at",
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
        "select": "id,org_id,source_id,status",
        "status": "eq.queued",
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
        "select": "id,org_id,url,is_enabled,cadence,next_run_at,last_run_at,etag,last_modified,content_type",
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
        "select": "id,org_id,name,type,url,is_enabled,cadence,next_run_at,last_run_at,created_at",
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
        "select": "id,org_id,source_id,run_id,fetched_url,content_hash,content_type,content_len,http_status,etag,last_modified,text_preview,text_fingerprint,fetched_at",
        "source_id": f"eq.{source_id}",
        "order": "fetched_at.desc",
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
        "select": "id,org_id,finding_id,status,owner_user_id,created_at,resolved_at",
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
        "select": "id,org_id,finding_id,status,owner_user_id,created_at,resolved_at",
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
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/audit_log"
    params = {
        "select": "id,org_id,actor_user_id,action,entity_type,entity_id,metadata,created_at",
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
            detail="Failed to fetch audit log from Supabase.",
        ) from exc

    return _validated_list_payload(response.json(), "Invalid audit log response from Supabase.")


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


async def rpc_append_audit(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/append_audit"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to write audit event in Supabase.",
        ) from exc


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
        "select": "id",
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
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/org_billing"
    params = {
        "select": "org_id,plan,subscription_status,current_period_end",
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
            detail="Failed to fetch billing state from Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid billing response from Supabase.")
    return rows[0] if rows else None


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
