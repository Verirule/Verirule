from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

import uvicorn

from app.core.logging import configure_logging, get_logger
from app.core.settings import get_settings
from app.core.supabase_rest import upsert_system_status
from app.worker.export_processor import EXPORT_BATCH_LIMIT, ExportProcessor
from app.worker.run_processor import MonitorRunProcessor

logger = get_logger("worker.supervisor")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        message = "worker error"
    return message[:500]


async def run_worker_tick(
    monitor_processor: MonitorRunProcessor,
    export_processor: ExportProcessor,
    *,
    run_batch_limit: int,
) -> dict[str, object]:
    tick_started_at = _now_iso()
    errors = 0
    due_sources = 0
    runs_queued = 0
    runs_processed = 0
    exports_processed = 0

    try:
        due_sources = await monitor_processor.count_due_sources_once()
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_due_sources_error",
            extra={"component": "worker", "error": _safe_error_message(exc)},
        )

    try:
        runs_queued = await monitor_processor.queue_due_sources_once(limit=10)
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_queue_runs_error",
            extra={"component": "worker", "error": _safe_error_message(exc)},
        )

    try:
        runs_processed = await monitor_processor.process_queued_runs_once(limit=run_batch_limit)
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_process_runs_error",
            extra={"component": "worker", "error": _safe_error_message(exc)},
        )

    try:
        exports_processed = await export_processor.process_queued_exports_once(limit=EXPORT_BATCH_LIMIT)
    except Exception as exc:  # pragma: no cover - defensive guard
        errors += 1
        logger.error(
            "worker.tick_process_exports_error",
            extra={"component": "worker", "error": _safe_error_message(exc)},
        )

    tick_finished_at = _now_iso()
    payload: dict[str, object] = {
        "mode": "worker",
        "tick_started_at": tick_started_at,
        "tick_finished_at": tick_finished_at,
        "runs_processed": runs_processed,
        "exports_processed": exports_processed,
        "runs_queued": runs_queued,
        "due_sources": due_sources,
        "errors": errors,
    }

    try:
        await upsert_system_status("worker", payload)
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error(
            "worker.heartbeat_error",
            extra={"component": "worker", "error": _safe_error_message(exc)},
        )

    return payload


async def run_worker_supervisor_loop() -> None:
    settings = get_settings()
    read_access_token = settings.WORKER_SUPABASE_ACCESS_TOKEN or settings.SUPABASE_SERVICE_ROLE_KEY
    if not read_access_token:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must be configured for worker mode")
    write_access_token = settings.SUPABASE_SERVICE_ROLE_KEY or read_access_token

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

    while True:
        payload = await run_worker_tick(
            monitor_processor,
            export_processor,
            run_batch_limit=settings.WORKER_BATCH_LIMIT,
        )

        if (
            int(payload.get("runs_processed") or 0) == 0
            and int(payload.get("exports_processed") or 0) == 0
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
