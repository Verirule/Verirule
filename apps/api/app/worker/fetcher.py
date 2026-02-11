from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import httpx


class UnsafeUrlError(ValueError):
    pass


def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def resolve_public_ips(host: str) -> list[ipaddress._BaseAddress]:
    try:
        results = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeUrlError("host resolution failed") from exc

    ips: list[ipaddress._BaseAddress] = []
    for result in results:
        sockaddr = result[4]
        if not sockaddr:
            continue
        ip = ipaddress.ip_address(sockaddr[0])
        if _is_blocked_ip(ip):
            raise UnsafeUrlError(f"blocked IP address: {ip}")
        ips.append(ip)

    if not ips:
        raise UnsafeUrlError("host has no routable IP addresses")
    return ips


def validate_fetch_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeUrlError("only http/https URLs are allowed")
    if not parsed.hostname:
        raise UnsafeUrlError("missing URL host")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("credentials in URL are not allowed")

    host = parsed.hostname.strip().lower()
    if host == "localhost" or host.endswith(".local"):
        raise UnsafeUrlError("localhost and .local hosts are blocked")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        resolve_public_ips(host)
    else:
        if _is_blocked_ip(ip):
            raise UnsafeUrlError(f"blocked IP address: {ip}")

    return url


async def fetch_url(
    url: str,
    etag: str | None = None,
    last_modified: str | None = None,
    *,
    timeout_seconds: float = 10.0,
    max_bytes: int = 1_000_000,
) -> dict[str, Any]:
    safe_url = validate_fetch_url(url)
    timeout = httpx.Timeout(timeout_seconds)
    headers: dict[str, str] = {
        "User-Agent": "VeriruleMonitor/1.0",
        "Accept-Encoding": "gzip, deflate",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    content = bytearray()
    fetched_url = safe_url
    response_status = 0
    response_content_type: str | None = None
    response_etag: str | None = None
    response_last_modified: str | None = None

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        async with client.stream("GET", safe_url, headers=headers) as response:
            if 300 <= response.status_code < 400 and response.status_code != 304:
                raise UnsafeUrlError("redirects are not allowed")
            if response.status_code not in {200, 304}:
                response.raise_for_status()

            fetched_url = str(response.url)
            response_status = int(response.status_code)
            response_content_type = response.headers.get("content-type")
            response_etag = response.headers.get("etag") or etag
            response_last_modified = response.headers.get("last-modified") or last_modified

            if response_status == 304:
                return {
                    "status": response_status,
                    "bytes": b"",
                    "content_type": response_content_type,
                    "etag": response_etag,
                    "last_modified": response_last_modified,
                    "fetched_url": fetched_url,
                }

            declared_len = response.headers.get("content-length")
            if declared_len and declared_len.isdigit() and int(declared_len) > max_bytes:
                raise UnsafeUrlError("response exceeds maximum size")

            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise UnsafeUrlError("response exceeds maximum size")

    return {
        "status": response_status,
        "bytes": bytes(content),
        "content_type": response_content_type,
        "etag": response_etag,
        "last_modified": response_last_modified,
        "fetched_url": fetched_url,
    }
