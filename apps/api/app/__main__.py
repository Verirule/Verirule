from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

import uvicorn

from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings
from app.core.supabase_rest import rpc_acquire_worker_lock, upsert_system_status
from app.worker.alert_task_processor import ALERT_TASK_BATCH_LIMIT, AlertTaskProcessor
from app.worker.digest_processor import DigestProcessor
from app.worker.export_processor import EXPORT_BATCH_LIMIT, ExportProcessor
from app.worker.notification_sender import NotificationSender
from app.worker.readiness_processor import ReadinessProcessor
from app.worker.retry import sanitize_error
from app.worker.run_processor import MonitorRunProcessor
from app.worker.sla_processor import SLAProcessor

logger = get_logger("worker.supervisor")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _worker_holder() -> str:
    alloc = os.getenv("FLY_ALLOC_ID") or os.getenv("HOSTNAME") or "worker"
    return f"{alloc}:{os.getpid()}"


def _worker_lock_ttl_seconds() -> int:
    raw_value = os.getenv("WORKER_LOCK_TTL_SECONDS", "120").strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 120
    return max(30, parsed)


async def run_worker_tick(
    monitor_processor: MonitorRunProcessor,
    export_processor: ExportProcessor,
    alert_task_processor: AlertTaskProcessor,
    readiness_processor: ReadinessProcessor,
    digest_processor: DigestProcessor,
    sla_processor: SLAProcessor,
    notification_sender: NotificationSender,
    *,
    run_batch_limit: int,
    heartbeat_enabled: bool,
    lock_holder: str,
    lock_ttl_seconds: int,
) -> dict[str, object]:
    tick_started_at = _now_iso()
    errors = 0
    due_sources = 0
    runs_queued = 0
    runs_processed = 0
    exports_processed = 0
    alert_tasks_processed = 0
    readiness_computed = 0
    digests_sent = 0
    sla_escalations_queued = 0
    notification_emails_sent = 0

    async def _lock_acquired(lock_key: str) -> bool:
        nonlocal errors
        try:
            acquired = await rpc_acquire_worker_lock(lock_key, lock_holder, lock_ttl_seconds)
        except Exception as exc:  # pragma: no cover - defensive guard
            errors += 1
            logger.error(
                "worker.tick_lock_error",
                extra={
                    "component": "worker",
                    "lock_key": lock_key,
                    "error": sanitize_error(exc, default_message="worker lock error"),
                },
            )
            return False
        if not acquired:
            logger.info(
                "worker.tick_lock_skipped",
                extra={"component": "worker", "lock_key": lock_key, "holder": lock_holder},
            )
        return acquired

    if await _lock_acquired("worker:run_processor"):
        try:
            run_metrics = await monitor_processor.run_once(
                queue_limit=10,
                process_limit=run_batch_limit,
            )
            due_sources = int(run_metrics.get("due_sources") or 0)
            runs_queued = int(run_metrics.get("runs_queued") or 0)
            runs_processed = int(run_metrics.get("runs_processed") or 0)
        except Exception as exc:  # pragma: no cover - defensive guard
            errors += 1
            logger.error(
                "worker.tick_process_runs_error",
                extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
            )

    if await _lock_acquired("worker:export_processor"):
        try:
            exports_processed = await export_processor.run_once(limit=EXPORT_BATCH_LIMIT)
        except Exception as exc:  # pragma: no cover - defensive guard
            errors += 1
            logger.error(
                "worker.tick_process_exports_error",
                extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
            )

    if await _lock_acquired("worker:alert_task_processor"):
        try:
            alert_tasks_processed = await alert_task_processor.run_once(limit=ALERT_TASK_BATCH_LIMIT)
        except Exception as exc:  # pragma: no cover - defensive guard
            errors += 1
            logger.error(
                "worker.tick_process_alert_tasks_error",
                extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
            )

    if await _lock_acquired("worker:readiness_processor"):
        try:
            readiness_computed = await readiness_processor.run_once()
        except Exception as exc:  # pragma: no cover - defensive guard
            errors += 1
            logger.error(
                "worker.tick_process_readiness_error",
                extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
            )

    if await _lock_acquired("worker:digest_processor"):
        try:
            digests_sent = await digest_processor.run_once()
        except Exception as exc:  # pragma: no cover - defensive guard
            errors += 1
            logger.error(
                "worker.tick_process_digests_error",
                extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
            )

    if await _lock_acquired("worker:sla_processor"):
        try:
            sla_escalations_queued = await sla_processor.run_once()
        except Exception as exc:  # pragma: no cover - defensive guard
            errors += 1
            logger.error(
                "worker.tick_process_sla_error",
                extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
            )

    if await _lock_acquired("worker:notification_sender"):
        try:
            notification_emails_sent = await notification_sender.run_once()
        except Exception as exc:  # pragma: no cover - defensive guard
            errors += 1
            logger.error(
                "worker.tick_process_notification_jobs_error",
                extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
            )

    tick_finished_at = _now_iso()
    payload: dict[str, object] = {
        "mode": "worker",
        "tick_started_at": tick_started_at,
        "tick_finished_at": tick_finished_at,
        "runs_processed": runs_processed,
        "exports_processed": exports_processed,
        "alert_tasks_processed": alert_tasks_processed,
        "runs_queued": runs_queued,
        "due_sources": due_sources,
        "readiness_computed": readiness_computed,
        "digests_sent": digests_sent,
        "sla_escalations_queued": sla_escalations_queued,
        "notification_emails_sent": notification_emails_sent,
        "errors": errors,
    }

    if heartbeat_enabled:
        try:
            await upsert_system_status("worker", payload)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "worker.heartbeat_error",
                extra={
                    "component": "worker",
                    "error": sanitize_error(exc, default_message="worker heartbeat error"),
                },
            )

    return payload


async def run_worker_supervisor_loop() -> None:
    settings = get_settings()
    service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must be configured for worker mode")
    read_access_token = settings.WORKER_SUPABASE_ACCESS_TOKEN or service_role_key
    write_access_token = service_role_key
    heartbeat_enabled = True
    worker_holder = _worker_holder()
    lock_ttl_seconds = _worker_lock_ttl_seconds()

    monitor_processor = MonitorRunProcessor(
        access_token=read_access_token,
        write_access_token=write_access_token,
        fetch_timeout_seconds=settings.WORKER_FETCH_TIMEOUT_SECONDS,
        fetch_max_bytes=settings.WORKER_FETCH_MAX_BYTES,
    )
    export_processor = ExportProcessor(
        access_token=write_access_token,
        bucket_name=settings.EXPORTS_BUCKET_NAME,
    )
    alert_task_processor = AlertTaskProcessor(access_token=write_access_token)
    readiness_processor = ReadinessProcessor(
        access_token=write_access_token,
        interval_seconds=settings.READINESS_COMPUTE_INTERVAL_SECONDS,
    )
    digest_processor = DigestProcessor(
        access_token=write_access_token,
        send_hour_utc=settings.DIGEST_SEND_HOUR_UTC,
        batch_limit=settings.DIGEST_BATCH_LIMIT,
        interval_seconds=settings.DIGEST_PROCESSOR_INTERVAL_SECONDS,
    )
    sla_processor = SLAProcessor(
        access_token=write_access_token,
        interval_seconds=settings.SLA_CHECK_INTERVAL_SECONDS,
    )
    notification_sender = NotificationSender(
        access_token=write_access_token,
        batch_limit=settings.NOTIFY_JOB_BATCH_LIMIT,
        max_attempts=settings.NOTIFY_MAX_ATTEMPTS,
    )

    while True:
        payload = await run_worker_tick(
            monitor_processor,
            export_processor,
            alert_task_processor,
            readiness_processor,
            digest_processor,
            sla_processor,
            notification_sender,
            run_batch_limit=settings.WORKER_BATCH_LIMIT,
            heartbeat_enabled=heartbeat_enabled,
            lock_holder=worker_holder,
            lock_ttl_seconds=lock_ttl_seconds,
        )

        if (
            int(payload.get("runs_processed") or 0) == 0
            and int(payload.get("exports_processed") or 0) == 0
            and int(payload.get("alert_tasks_processed") or 0) == 0
            and int(payload.get("runs_queued") or 0) == 0
            and int(payload.get("readiness_computed") or 0) == 0
            and int(payload.get("digests_sent") or 0) == 0
            and int(payload.get("sla_escalations_queued") or 0) == 0
            and int(payload.get("notification_emails_sent") or 0) == 0
        ):
            await asyncio.sleep(max(1, settings.WORKER_POLL_INTERVAL_SECONDS))


def main() -> None:
    configure_logging()
    settings = get_settings()
    mode = settings.VERIRULE_MODE.strip().lower()

    if mode == "worker":
        asyncio.run(run_worker_supervisor_loop())
        return

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", str(settings.API_PORT)))
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
