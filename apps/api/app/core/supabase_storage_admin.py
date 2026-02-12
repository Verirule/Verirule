from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.core.settings import get_settings


def _service_role_key() -> str:
    settings = get_settings()
    service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not service_role_key or not service_role_key.strip():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Audit exports are not configured.",
        )
    return service_role_key


def _admin_headers(*, content_type: str | None = None) -> dict[str, str]:
    service_role_key = _service_role_key()
    headers = {
        "Authorization": f"Bearer {service_role_key}",
        "apikey": service_role_key,
        "Accept": "application/json",
    }
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _normalize_signed_url(url_value: str) -> str:
    settings = get_settings()
    base_url = settings.SUPABASE_URL.rstrip("/")
    if url_value.startswith("http://") or url_value.startswith("https://"):
        return url_value
    if url_value.startswith("/"):
        return f"{base_url}{url_value}"
    return f"{base_url}/{url_value}"


def _signed_url_from_payload(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid signed download URL response.",
        )

    signed_url = payload.get("signedURL")
    if not isinstance(signed_url, str) or not signed_url:
        signed_url = payload.get("signedUrl")
    if not isinstance(signed_url, str) or not signed_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid signed download URL response.",
        )
    return signed_url


def _error_message_from_response(response: httpx.Response, default: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        return default
    if not isinstance(payload, dict):
        return default
    detail = payload.get("message")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    detail = payload.get("error")
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return default


async def upload_bytes(bucket: str, path: str, data: bytes, content_type: str) -> None:
    settings = get_settings()
    encoded_bucket = quote(bucket, safe="")
    encoded_path = quote(path, safe="/")
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{encoded_bucket}/{encoded_path}"

    headers = _admin_headers(content_type=content_type)
    headers["x-upsert"] = "true"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, content=data, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload export file.",
        ) from exc


async def create_signed_download_url(bucket: str, path: str, expires: int) -> dict[str, str]:
    settings = get_settings()
    encoded_bucket = quote(bucket, safe="")
    encoded_path = quote(path, safe="/")
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/sign/{encoded_bucket}/{encoded_path}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={"expiresIn": expires},
                headers=_admin_headers(content_type="application/json"),
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create signed download URL.",
        ) from exc

    signed_url = _signed_url_from_payload(response.json())
    return {"path": path, "signed_url": _normalize_signed_url(signed_url)}


async def download_bytes(bucket: str, path: str) -> bytes:
    settings = get_settings()
    max_file_bytes = settings.AUDIT_PACKET_MAX_FILE_BYTES
    encoded_bucket = quote(bucket, safe="")
    encoded_path = quote(path, safe="/")
    url = f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/{encoded_bucket}/{encoded_path}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", url, headers=_admin_headers()) as response:
                if response.status_code == status.HTTP_404_NOT_FOUND:
                    detail = _error_message_from_response(response, "Evidence file was not found.")
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
                if response.status_code >= status.HTTP_400_BAD_REQUEST:
                    detail = _error_message_from_response(
                        response, "Failed to download evidence file."
                    )
                    raise HTTPException(status_code=response.status_code, detail=detail)

                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        declared_size = int(content_length)
                    except ValueError:
                        declared_size = None
                    if declared_size is not None and declared_size > max_file_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Evidence file exceeds maximum file size.",
                        )

                chunks = bytearray()
                async for chunk in response.aiter_bytes():
                    chunks.extend(chunk)
                    if len(chunks) > max_file_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Evidence file exceeds maximum file size.",
                        )
                return bytes(chunks)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to download evidence file.",
        ) from exc
