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
