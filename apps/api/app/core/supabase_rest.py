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
        "select": "id,org_id,name,type,url,is_enabled,created_at",
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


async def select_tasks(access_token: str, org_id: str) -> list[dict[str, Any]]:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/tasks"
    params = {
        "select": "id,org_id,title,status,assignee_user_id,alert_id,finding_id,due_at,created_by_user_id,created_at",
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
        "select": "id,task_id,type,ref,created_by_user_id,created_at",
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


async def count_alert_task_evidence(access_token: str, alert_id: str) -> int:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/tasks"
    params = {
        "select": "id,task_evidence(id)",
        "alert_id": f"eq.{alert_id}",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to evaluate alert evidence in Supabase.",
        ) from exc

    rows = _validated_list_payload(response.json(), "Invalid alert evidence response from Supabase.")
    evidence_total = 0
    for row in rows:
        nested = row.get("task_evidence")
        if nested is None:
            continue
        if not isinstance(nested, list):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid alert evidence response from Supabase.",
            )
        evidence_total += len(nested)
    return evidence_total


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


async def rpc_assign_task(access_token: str, payload: dict[str, Any]) -> None:
    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/assign_task"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=supabase_rest_headers(access_token))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to assign task in Supabase.",
        ) from exc


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
