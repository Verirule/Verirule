from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

from app.core.settings import get_settings
from app.core.supabase_rest import (
    rpc_append_audit,
    rpc_insert_snapshot,
    rpc_set_monitor_run_state,
    rpc_upsert_alert_for_finding,
    rpc_upsert_finding,
    select_latest_snapshot,
    select_queued_monitor_runs,
    select_source_by_id,
)


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


async def fetch_url_snapshot(
    url: str, *, timeout_seconds: float = 10.0, max_bytes: int = 1_000_000
) -> dict[str, object]:
    safe_url = validate_fetch_url(url)
    timeout = httpx.Timeout(timeout_seconds)
    headers = {"User-Agent": "VeriruleMonitor/1.0"}

    hasher = hashlib.sha256()
    content_len = 0
    content_type: str | None = None
    fetched_url = safe_url

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        async with client.stream("GET", safe_url, headers=headers) as response:
            if 300 <= response.status_code < 400:
                raise UnsafeUrlError("redirects are not allowed")
            response.raise_for_status()

            fetched_url = str(response.url)
            content_type = response.headers.get("content-type")
            declared_len = response.headers.get("content-length")
            if declared_len and declared_len.isdigit() and int(declared_len) > max_bytes:
                raise UnsafeUrlError("response exceeds maximum size")

            async for chunk in response.aiter_bytes():
                content_len += len(chunk)
                if content_len > max_bytes:
                    raise UnsafeUrlError("response exceeds maximum size")
                hasher.update(chunk)

    return {
        "fetched_url": fetched_url,
        "content_hash": hasher.hexdigest(),
        "content_type": content_type,
        "content_len": content_len,
    }


@dataclass
class MonitorRunProcessor:
    access_token: str
    write_access_token: str | None = None
    fetch_timeout_seconds: float = 10.0
    fetch_max_bytes: int = 1_000_000

    @property
    def write_token(self) -> str:
        return self.write_access_token or self.access_token

    async def process_queued_runs_once(self, limit: int = 5) -> int:
        runs = await select_queued_monitor_runs(self.access_token, limit=limit)
        for run in runs:
            await self._process_single_run(run)
        return len(runs)

    async def _process_single_run(self, run: dict[str, object]) -> None:
        run_id = str(run["id"])
        org_id = str(run["org_id"])
        source_id = str(run["source_id"])

        await rpc_set_monitor_run_state(
            self.write_token,
            {"p_run_id": run_id, "p_status": "running", "p_error": None},
        )

        try:
            source = await select_source_by_id(self.access_token, source_id)
            if not source or str(source.get("org_id")) != org_id:
                raise ValueError("source not found in org")
            if source.get("is_enabled") is False:
                raise ValueError("source is disabled")

            source_url = str(source.get("url") or "").strip()
            if not source_url:
                raise ValueError("source URL is empty")

            snapshot = await fetch_url_snapshot(
                source_url,
                timeout_seconds=self.fetch_timeout_seconds,
                max_bytes=self.fetch_max_bytes,
            )
            previous_snapshot = await select_latest_snapshot(self.access_token, source_id)

            await rpc_insert_snapshot(
                self.write_token,
                {
                    "p_org_id": org_id,
                    "p_source_id": source_id,
                    "p_run_id": run_id,
                    "p_fetched_url": snapshot["fetched_url"],
                    "p_content_hash": snapshot["content_hash"],
                    "p_content_type": snapshot["content_type"],
                    "p_content_len": int(snapshot["content_len"]),
                },
            )

            previous_hash = (
                str(previous_snapshot.get("content_hash")) if previous_snapshot else None
            )
            current_hash = str(snapshot["content_hash"])
            if previous_hash != current_hash:
                fingerprint = hashlib.sha256(f"{source_id}:{current_hash}".encode()).hexdigest()
                finding_id = await rpc_upsert_finding(
                    self.write_token,
                    {
                        "p_org_id": org_id,
                        "p_source_id": source_id,
                        "p_run_id": run_id,
                        "p_title": "Source content changed",
                        "p_summary": f"Detected content hash change for monitored source {source_id}.",
                        "p_severity": "medium",
                        "p_fingerprint": fingerprint,
                        "p_raw_url": str(snapshot["fetched_url"]),
                        "p_raw_hash": current_hash,
                    },
                )
                alert_result = await rpc_upsert_alert_for_finding(
                    self.write_token,
                    {"p_org_id": org_id, "p_finding_id": finding_id},
                )
                await rpc_append_audit(
                    self.write_token,
                    {
                        "p_org_id": org_id,
                        "p_action": "worker_finding_detected",
                        "p_entity_type": "monitor_run",
                        "p_entity_id": run_id,
                        "p_metadata": {
                            "source_id": source_id,
                            "finding_id": finding_id,
                            "alert_id": alert_result["id"],
                        },
                    },
                )

            await rpc_set_monitor_run_state(
                self.write_token,
                {"p_run_id": run_id, "p_status": "succeeded", "p_error": None},
            )
        except (HTTPException, ValueError, httpx.HTTPError) as exc:
            await rpc_set_monitor_run_state(
                self.write_token,
                {
                    "p_run_id": run_id,
                    "p_status": "failed",
                    "p_error": str(exc)[:1000],
                },
            )
        except Exception as exc:  # pragma: no cover - catch-all safety
            await rpc_set_monitor_run_state(
                self.write_token,
                {
                    "p_run_id": run_id,
                    "p_status": "failed",
                    "p_error": f"unexpected worker error: {exc}"[:1000],
                },
            )


async def run_worker_loop() -> None:
    settings = get_settings()
    read_access_token = settings.WORKER_SUPABASE_ACCESS_TOKEN or settings.SUPABASE_SERVICE_ROLE_KEY
    if not read_access_token:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY must be configured for worker mode"
        )
    write_access_token = settings.SUPABASE_SERVICE_ROLE_KEY or read_access_token

    processor = MonitorRunProcessor(
        access_token=read_access_token,
        write_access_token=write_access_token,
        fetch_timeout_seconds=settings.WORKER_FETCH_TIMEOUT_SECONDS,
        fetch_max_bytes=settings.WORKER_FETCH_MAX_BYTES,
    )

    while True:
        try:
            processed = await processor.process_queued_runs_once(limit=settings.WORKER_BATCH_LIMIT)
        except Exception as exc:  # pragma: no cover - loop resiliency
            print(f"worker loop error: {exc}")
            await asyncio.sleep(max(1, settings.WORKER_POLL_INTERVAL_SECONDS))
            continue
        if processed == 0:
            await asyncio.sleep(max(1, settings.WORKER_POLL_INTERVAL_SECONDS))
