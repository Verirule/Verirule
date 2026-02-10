from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.core.settings import get_settings


def get_storage_admin_headers() -> dict[str, str]:
    settings = get_settings()
    service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not service_role_key or not service_role_key.strip():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="File evidence uploads are not configured.",
        )

    return {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _normalize_signed_url(url_value: str) -> str:
    settings = get_settings()
    base_url = settings.SUPABASE_URL.rstrip("/")
    if url_value.startswith("http://") or url_value.startswith("https://"):
        return url_value
    if url_value.startswith("/"):
        return f"{base_url}{url_value}"
    return f"{base_url}/{url_value}"


def _validated_signed_url_payload(payload: Any, error_message: str) -> str:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error_message)

    signed_url = payload.get("signedURL")
    if not isinstance(signed_url, str) or not signed_url:
        signed_url = payload.get("signedUrl")

    if not isinstance(signed_url, str) or not signed_url:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error_message)

    return signed_url


async def create_signed_upload_url(bucket: str, path: str, expires_in: int) -> dict[str, str]:
    settings = get_settings()
    encoded_bucket = quote(bucket, safe="")
    encoded_path = quote(path, safe="/")
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/sign/{encoded_bucket}/{encoded_path}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={"expiresIn": expires_in},
                headers=get_storage_admin_headers(),
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create signed upload URL.",
        ) from exc

    signed_url = _validated_signed_url_payload(response.json(), "Invalid signed upload URL response.")
    return {"path": path, "signed_url": _normalize_signed_url(signed_url)}


async def create_signed_download_url(bucket: str, path: str, expires_in: int) -> dict[str, str]:
    settings = get_settings()
    encoded_bucket = quote(bucket, safe="")
    encoded_path = quote(path, safe="/")
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/sign/{encoded_bucket}/{encoded_path}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={"expiresIn": expires_in},
                headers=get_storage_admin_headers(),
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create signed download URL.",
        ) from exc

    signed_url = _validated_signed_url_payload(response.json(), "Invalid signed download URL response.")
    return {"path": path, "signed_url": _normalize_signed_url(signed_url)}
