from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

import uvicorn

from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings
from app.core.supabase_rest import upsert_system_status
from app.worker.alert_task_processor import ALERT_TASK_BATCH_LIMIT, AlertTaskProcessor
from app.worker.export_processor import EXPORT_BATCH_LIMIT, ExportProcessor
from app.worker.retry import sanitize_error
from app.worker.run_processor import MonitorRunProcessor

logger = get_logger("worker.supervisor")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


async def run_worker_tick(
    monitor_processor: MonitorRunProcessor,
    export_processor: ExportProcessor,
    alert_task_processor: AlertTaskProcessor,
    *,
    run_batch_limit: int,
    heartbeat_enabled: bool,
) -> dict[str, object]:
    tick_started_at = _now_iso()
    errors = 0
    due_sources = 0
    runs_queued = 0
    runs_processed = 0
    exports_processed = 0
    alert_tasks_processed = 0

    try:
        due_sources = await monitor_processor.count_due_sources_once()
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_due_sources_error",
            extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
        )

    try:
        runs_queued = await monitor_processor.queue_due_sources_once(limit=10)
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_queue_runs_error",
            extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
        )

    try:
        runs_processed = await monitor_processor.process_queued_runs_once(limit=run_batch_limit)
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_process_runs_error",
            extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
        )

    try:
        exports_processed = await export_processor.process_queued_exports_once(limit=EXPORT_BATCH_LIMIT)
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_process_exports_error",
            extra={"component": "worker", "error": sanitize_error(exc, default_message="worker error")},
        )

    try:
        alert_tasks_processed = await alert_task_processor.process_alerts_once(limit=ALERT_TASK_BATCH_LIMIT)
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_process_alert_tasks_error",
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
    read_access_token = settings.WORKER_SUPABASE_ACCESS_TOKEN or settings.SUPABASE_SERVICE_ROLE_KEY
    if not read_access_token:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must be configured for worker mode")
    write_access_token = settings.SUPABASE_SERVICE_ROLE_KEY or read_access_token
    heartbeat_enabled = bool(settings.SUPABASE_SERVICE_ROLE_KEY)
    if not heartbeat_enabled:
        logger.error(
            "worker.heartbeat_disabled",
            extra={
                "component": "worker",
                "reason": "SUPABASE_SERVICE_ROLE_KEY missing; heartbeat skipped",
            },
        )

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

    while True:
        payload = await run_worker_tick(
            monitor_processor,
            export_processor,
            alert_task_processor,
            run_batch_limit=settings.WORKER_BATCH_LIMIT,
            heartbeat_enabled=heartbeat_enabled,
        )

        if (
            int(payload.get("runs_processed") or 0) == 0
            and int(payload.get("exports_processed") or 0) == 0
            and int(payload.get("alert_tasks_processed") or 0) == 0
            and int(payload.get("runs_queued") or 0) == 0
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
