from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.settings import get_settings


def _service_role_key() -> str:
    settings = get_settings()
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not key or not key.strip():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Supabase admin auth is not configured.",
        )
    return key.strip()


def _admin_headers() -> dict[str, str]:
    key = _service_role_key()
    return {
        "Authorization": f"Bearer {key}",
        "apikey": key,
        "Accept": "application/json",
    }


def _extract_email(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None

    direct_email = payload.get("email")
    if isinstance(direct_email, str) and direct_email.strip():
        return direct_email.strip().lower()

    user_row = payload.get("user")
    if isinstance(user_row, dict):
        nested_email = user_row.get("email")
        if isinstance(nested_email, str) and nested_email.strip():
            return nested_email.strip().lower()
    return None


async def fetch_user_email_by_id(
    user_id: str,
    *,
    cache: dict[str, str | None] | None = None,
) -> str | None:
    user_id_value = user_id.strip()
    if not user_id_value:
        return None
    if cache is not None and user_id_value in cache:
        return cache[user_id_value]

    settings = get_settings()
    url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id_value}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=_admin_headers())
            if response.status_code == status.HTTP_404_NOT_FOUND:
                if cache is not None:
                    cache[user_id_value] = None
                return None
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch user email from Supabase Auth.",
        ) from exc

    email = _extract_email(response.json())
    if cache is not None:
        cache[user_id_value] = email
    return email

