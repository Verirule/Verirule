from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.core.supabase_rest import (
    clear_monitor_run_error_state,
    enqueue_notification_job,
    ensure_org_notification_rules,
    get_org_notification_rules,
    mark_monitor_run_attempt_started,
    mark_monitor_run_dead_letter,
    mark_monitor_run_for_retry,
    rpc_append_audit,
    rpc_create_monitor_run,
    rpc_insert_finding_explanation,
    rpc_insert_snapshot_v3,
    rpc_schedule_next_run,
    rpc_set_monitor_run_state,
    rpc_set_source_fetch_metadata,
    rpc_upsert_alert_for_finding,
    rpc_upsert_finding,
    select_due_sources,
    select_latest_snapshot,
    select_queued_monitor_runs,
    select_recent_active_monitor_runs_for_source,
    select_source_by_id,
)
from app.worker.adapters.base import Snapshot, Source
from app.worker.adapters.registry import get_adapter
from app.worker.explain import build_explanation
from app.worker.fetcher import UnsafeUrlError
from app.worker.retry import backoff_seconds, sanitize_error

MAX_RUN_ATTEMPTS = 5
logger = get_logger("worker.runs")
_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


@dataclass
class MonitorRunProcessor:
    access_token: str
    write_access_token: str | None = None
    fetch_timeout_seconds: float = 10.0
    fetch_max_bytes: int = 1_000_000

    @property
    def write_token(self) -> str:
        return self.write_access_token or self.access_token

    async def count_due_sources_once(self) -> int:
        due_sources = await select_due_sources(self.access_token)
        return len(due_sources)

    async def queue_due_sources_once(self, limit: int = 10) -> int:
        due_sources = await select_due_sources(self.access_token)
        queued_count = 0
        created_after = (datetime.now(UTC) - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")

        for source in due_sources:
            if queued_count >= limit:
                break

            source_id = str(source.get("id") or "")
            org_id = str(source.get("org_id") or "")
            if not source_id or not org_id:
                continue

            active_runs = await select_recent_active_monitor_runs_for_source(
                self.access_token,
                source_id,
                created_after,
            )
            if active_runs:
                continue

            await rpc_create_monitor_run(
                self.write_token,
                {"p_org_id": org_id, "p_source_id": source_id},
            )
            await rpc_schedule_next_run(self.write_token, {"p_source_id": source_id})
            queued_count += 1

        return queued_count

    async def process_queued_runs_once(self, limit: int = 5) -> int:
        runs = await select_queued_monitor_runs(self.access_token, limit=limit)
        for run in runs:
            await self._process_single_run(run)
        return len(runs)

    async def _process_single_run(self, run: dict[str, object]) -> None:
        run_id = str(run["id"])
        org_id = str(run["org_id"])
        source_id = str(run["source_id"])
        current_attempts = _safe_int(run.get("attempts"))
        attempt_number = current_attempts + 1

        await mark_monitor_run_attempt_started(run_id, attempt_number)
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

            source_payload = dict(source)
            source_payload["fetch_timeout_seconds"] = self.fetch_timeout_seconds
            source_payload["fetch_max_bytes"] = self.fetch_max_bytes
            source_model = Source.model_validate(source_payload)
            previous_snapshot_row = await select_latest_snapshot(self.access_token, source_id)
            previous_snapshot = (
                Snapshot.model_validate(previous_snapshot_row) if previous_snapshot_row else None
            )
            adapter = get_adapter(source_model.kind)
            adapter_result = await adapter.fetch(source_model, previous_snapshot)

            status_code = int(adapter_result.http_status)
            response_etag = adapter_result.etag
            response_last_modified = adapter_result.last_modified
            response_content_type = adapter_result.content_type

            await rpc_set_source_fetch_metadata(
                self.write_token,
                {
                    "p_source_id": source_id,
                    "p_etag": response_etag,
                    "p_last_modified": response_last_modified,
                    "p_content_type": response_content_type,
                },
            )

            if status_code == 304:
                await rpc_set_monitor_run_state(
                    self.write_token,
                    {"p_run_id": run_id, "p_status": "succeeded", "p_error": None},
                )
                await clear_monitor_run_error_state(run_id)
                return

            if source_model.kind in {"rss", "github_releases"} and previous_snapshot:
                previous_item_id = (previous_snapshot.item_id or "").strip()
                current_item_id = (adapter_result.item_id or "").strip()
                if previous_item_id and current_item_id and previous_item_id == current_item_id:
                    await rpc_set_monitor_run_state(
                        self.write_token,
                        {"p_run_id": run_id, "p_status": "succeeded", "p_error": None},
                    )
                    await clear_monitor_run_error_state(run_id)
                    return

            canonical_text = (adapter_result.canonical_text or "").strip()
            if canonical_text:
                current_fingerprint = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
            elif adapter_result.raw_bytes_hash:
                current_fingerprint = adapter_result.raw_bytes_hash
            else:
                fallback_bytes = (adapter_result.item_id or "").encode("utf-8")
                current_fingerprint = hashlib.sha256(fallback_bytes).hexdigest()

            previous_fingerprint = None
            if previous_snapshot:
                previous_fingerprint = (
                    previous_snapshot.text_fingerprint or previous_snapshot.content_hash or ""
                ).strip() or None

            await rpc_insert_snapshot_v3(
                self.write_token,
                {
                    "p_org_id": org_id,
                    "p_source_id": source_id,
                    "p_run_id": run_id,
                    "p_fetched_url": adapter_result.fetched_url or source_url,
                    "p_content_hash": current_fingerprint,
                    "p_content_type": response_content_type,
                    "p_content_len": int(adapter_result.content_len),
                    "p_http_status": status_code,
                    "p_etag": response_etag,
                    "p_last_modified": response_last_modified,
                    "p_text_preview": canonical_text[:2000],
                    "p_text_fingerprint": current_fingerprint,
                    "p_canonical_title": adapter_result.canonical_title,
                    "p_canonical_text": canonical_text,
                    "p_item_id": adapter_result.item_id,
                    "p_item_published_at": (
                        adapter_result.item_published_at.isoformat()
                        if adapter_result.item_published_at
                        else None
                    ),
                },
            )

            if previous_fingerprint != current_fingerprint:
                finding_fingerprint = hashlib.sha256(
                    f"{source_id}:{current_fingerprint}".encode()
                ).hexdigest()
                finding_severity = "medium"
                previous_text = ""
                if previous_snapshot:
                    previous_text = previous_snapshot.canonical_text or previous_snapshot.text_preview or ""
                explanation = build_explanation(previous_text, canonical_text)
                finding_id = await rpc_upsert_finding(
                    self.write_token,
                    {
                        "p_org_id": org_id,
                        "p_source_id": source_id,
                        "p_run_id": run_id,
                        "p_title": "Source content changed",
                        "p_summary": str(explanation["summary"]),
                        "p_severity": finding_severity,
                        "p_fingerprint": finding_fingerprint,
                        "p_raw_url": adapter_result.fetched_url or source_url,
                        "p_raw_hash": current_fingerprint,
                    },
                )
                await rpc_insert_finding_explanation(
                    self.write_token,
                    {
                        "p_org_id": org_id,
                        "p_finding_id": finding_id,
                        "p_summary": str(explanation["summary"]),
                        "p_diff_preview": explanation.get("diff_preview"),
                        "p_citations": explanation.get("citations") or [],
                    },
                )
                alert_result = await rpc_upsert_alert_for_finding(
                    self.write_token,
                    {"p_org_id": org_id, "p_finding_id": finding_id},
                )
                alert_id = str(alert_result.get("id") or "").strip()
                if alert_id:
                    try:
                        await self._enqueue_immediate_alert_if_needed(
                            org_id=org_id,
                            alert_id=alert_id,
                            severity=finding_severity,
                        )
                    except Exception as exc:
                        logger.warning(
                            "run.immediate_alert_queue_failed",
                            extra={
                                "component": "worker",
                                "org_id": org_id,
                                "alert_id": alert_id,
                                "error": sanitize_error(
                                    exc,
                                    default_message="immediate alert queue failed",
                                ),
                            },
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
                            "alert_id": alert_id,
                        },
                    },
                )

            await rpc_set_monitor_run_state(
                self.write_token,
                {"p_run_id": run_id, "p_status": "succeeded", "p_error": None},
            )
            await clear_monitor_run_error_state(run_id)
        except (UnsafeUrlError, ValueError, httpx.HTTPError) as exc:
            error_text = sanitize_error(exc, default_message="Monitor run failed.")
            if attempt_number < MAX_RUN_ATTEMPTS:
                next_attempt_at = _retry_at_iso(attempt_number)
                await mark_monitor_run_for_retry(run_id, attempt_number, next_attempt_at, error_text)
                logger.warning(
                    "run.retry_scheduled",
                    extra={
                        "component": "worker",
                        "run_id": run_id,
                        "attempts": attempt_number,
                        "next_attempt_at": next_attempt_at,
                    },
                )
                return
            await mark_monitor_run_dead_letter(run_id, attempt_number, error_text, _now_iso())
            logger.error(
                "run.dead_letter",
                extra={
                    "component": "worker",
                    "run_id": run_id,
                    "attempts": attempt_number,
                    "last_error": error_text,
                },
            )
        except Exception as exc:  # pragma: no cover - catch-all safety
            error_text = sanitize_error(exc, default_message="Monitor run failed.")
            if attempt_number < MAX_RUN_ATTEMPTS:
                next_attempt_at = _retry_at_iso(attempt_number)
                await mark_monitor_run_for_retry(run_id, attempt_number, next_attempt_at, error_text)
                logger.warning(
                    "run.retry_scheduled",
                    extra={
                        "component": "worker",
                        "run_id": run_id,
                        "attempts": attempt_number,
                        "next_attempt_at": next_attempt_at,
                    },
                )
                return
            await mark_monitor_run_dead_letter(run_id, attempt_number, error_text, _now_iso())
            logger.error(
                "run.dead_letter",
                extra={
                    "component": "worker",
                    "run_id": run_id,
                    "attempts": attempt_number,
                    "last_error": error_text,
                },
            )

    async def _enqueue_immediate_alert_if_needed(
        self,
        *,
        org_id: str,
        alert_id: str,
        severity: str,
    ) -> None:
        await ensure_org_notification_rules(self.write_token, org_id)
        rules = await get_org_notification_rules(self.write_token, org_id)
        if not isinstance(rules, dict):
            return
        if not bool(rules.get("enabled", True)):
            return

        mode = str(rules.get("mode") or "digest").strip().lower()
        if mode not in {"immediate", "both"}:
            return

        min_severity = str(rules.get("min_severity") or "medium")
        if not _severity_meets_minimum(severity=severity, min_severity=min_severity):
            return

        await enqueue_notification_job(
            org_id,
            "immediate_alert",
            {
                "org_id": org_id,
                "alert_id": alert_id,
                "entity_type": "alert",
                "entity_id": alert_id,
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
            await processor.queue_due_sources_once(limit=10)
            processed = await processor.process_queued_runs_once(limit=settings.WORKER_BATCH_LIMIT)
        except Exception as exc:  # pragma: no cover - loop resiliency
            logger.error(
                "run.worker_loop_error",
                extra={
                    "component": "worker",
                    "error": sanitize_error(exc, default_message="Monitor run loop failed."),
                },
            )
            await asyncio.sleep(max(1, settings.WORKER_POLL_INTERVAL_SECONDS))
            continue
        if processed == 0:
            await asyncio.sleep(max(1, settings.WORKER_POLL_INTERVAL_SECONDS))


def _safe_int(value: object | None) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _severity_meets_minimum(*, severity: str, min_severity: str) -> bool:
    threshold = _SEVERITY_RANK.get(min_severity.strip().lower(), _SEVERITY_RANK["medium"])
    score = _SEVERITY_RANK.get(severity.strip().lower(), _SEVERITY_RANK["medium"])
    return score >= threshold


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _retry_at_iso(attempt_number: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=backoff_seconds(attempt_number))).isoformat().replace(
        "+00:00", "Z"
    )
