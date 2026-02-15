from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger
from app.core.supabase_rest import list_active_org_ids_service, rpc_compute_org_readiness
from app.worker.retry import sanitize_error

logger = get_logger("worker.readiness")


class ReadinessProcessor:
    def __init__(self, *, access_token: str, interval_seconds: int = 900) -> None:
        self.access_token = access_token
        self.interval_seconds = max(1, interval_seconds)
        self._next_compute_at: datetime = datetime.now(UTC)

    def _is_due(self, now: datetime) -> bool:
        return now >= self._next_compute_at

    async def process_if_due(self) -> int:
        now = datetime.now(UTC)
        if not self._is_due(now):
            return 0

        computed_count = 0
        try:
            org_ids = await list_active_org_ids_service()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error(
                "readiness.active_orgs_error",
                extra={
                    "component": "worker",
                    "error": sanitize_error(exc, default_message="readiness active org query failed"),
                },
            )
            self._next_compute_at = now + timedelta(seconds=self.interval_seconds)
            return 0

        for org_id in org_ids:
            try:
                await rpc_compute_org_readiness(self.access_token, org_id)
                computed_count += 1
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning(
                    "readiness.compute_failed",
                    extra={
                        "component": "worker",
                        "org_id": org_id,
                        "error": sanitize_error(exc, default_message="readiness compute failed"),
                    },
                )

        self._next_compute_at = now + timedelta(seconds=self.interval_seconds)
        return computed_count

    async def run_once(self) -> int:
        return await self.process_if_due()
