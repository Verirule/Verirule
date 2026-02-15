from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.core.supabase_rest import (
    mark_audit_export_attempt_started,
    mark_audit_export_dead_letter,
    mark_audit_export_for_retry,
    select_audit_packet_data,
    select_queued_audit_exports_service,
    update_audit_export_status,
)
from app.core.supabase_storage_admin import download_bytes, upload_bytes
from app.exports.generate import build_csv, build_export_bytes, build_pdf
from app.exports.packet import build_zip
from app.worker.retry import backoff_seconds, sanitize_error

EXPORT_BATCH_LIMIT = 3
MAX_EXPORT_ATTEMPTS = 5
logger = get_logger("worker.exports")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _normalize_iso8601(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None

    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sanitize_error_text(exc: Exception) -> str:
    return sanitize_error(exc, default_message="Export generation failed.")


def _scope_include(scope: dict[str, Any]) -> list[str]:
    include = scope.get("include")
    if not isinstance(include, list):
        return []
    values: list[str] = []
    for item in include:
        if isinstance(item, str) and item.strip():
            values.append(item.strip().lower())
    return values


def _apply_include_scope(packet: dict[str, Any], include: list[str]) -> dict[str, Any]:
    if not include:
        return packet

    aliases = {
        "findings": "findings",
        "alerts": "alerts",
        "tasks": "tasks",
        "evidence": "evidence_files",
        "evidence_files": "evidence_files",
        "task_evidence": "task_evidence",
        "comments": "task_comments",
        "runs": "runs",
        "snapshots": "snapshots",
        "timeline": "audit_timeline",
        "audit_timeline": "audit_timeline",
    }
    selected = {aliases[item] for item in include if item in aliases}
    if "evidence_files" in selected:
        selected.add("task_evidence")
    list_keys = {
        "findings",
        "alerts",
        "tasks",
        "task_evidence",
        "evidence_files",
        "task_comments",
        "runs",
        "snapshots",
        "audit_timeline",
    }
    for key in list_keys:
        if key not in selected:
            packet[key] = []
    if "findings" not in selected:
        packet["finding_explanations"] = []
    return packet


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


def _retry_at_iso(attempt_number: int) -> str:
    return (datetime.now(UTC) + timedelta(seconds=backoff_seconds(attempt_number))).isoformat().replace(
        "+00:00", "Z"
    )


def _safe_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


class ExportProcessor:
    def __init__(self, *, access_token: str, bucket_name: str) -> None:
        self.access_token = access_token
        self.bucket_name = bucket_name

    async def process_queued_exports_once(self, limit: int = EXPORT_BATCH_LIMIT) -> int:
        export_rows = await select_queued_audit_exports_service(limit=limit)
        for row in export_rows:
            await self._process_single_export(row)
        return len(export_rows)

    async def run_once(self, *, limit: int = EXPORT_BATCH_LIMIT) -> int:
        return await self.process_queued_exports_once(limit=limit)

    async def _process_single_export(self, row: dict[str, Any]) -> None:
        export_id = str(row.get("id") or "")
        org_id = str(row.get("org_id") or "")
        export_format = str(row.get("format") or "").lower()
        scope = row.get("scope") if isinstance(row.get("scope"), dict) else {}
        include = _scope_include(scope)
        current_attempts = _safe_int(row.get("attempts"))
        attempt_number = current_attempts + 1

        if not export_id or not org_id or export_format not in {"csv", "pdf", "zip"}:
            return

        await mark_audit_export_attempt_started(export_id, attempt_number)

        try:
            from_ts = _normalize_iso8601(scope.get("from"))
            to_ts = _normalize_iso8601(scope.get("to"))
            packet = await select_audit_packet_data(self.access_token, org_id, from_ts, to_ts)
            packet["export_id"] = export_id
            packet["generated_at"] = _now_iso()
            packet["scope"] = scope
            packet["include"] = include
            packet = _apply_include_scope(packet, include)

            content, sha256, extension, content_type = await self._build_export_content(
                export_format=export_format,
                packet=packet,
            )
            file_path = f"org/{org_id}/exports/{export_id}.{extension}"
            await upload_bytes(self.bucket_name, file_path, content, content_type)

            await update_audit_export_status(
                export_id,
                status_value="succeeded",
                file_path=file_path,
                file_sha256=sha256,
                error_text=None,
                completed_at=_now_iso(),
            )
        except Exception as exc:
            error_text = _sanitize_error_text(exc)
            if attempt_number < MAX_EXPORT_ATTEMPTS:
                next_attempt_at = _retry_at_iso(attempt_number)
                await mark_audit_export_for_retry(
                    export_id,
                    attempts=attempt_number,
                    next_attempt_at=next_attempt_at,
                    last_error=error_text,
                )
                logger.warning(
                    "export.retry_scheduled",
                    extra={
                        "component": "worker",
                        "export_id": export_id,
                        "attempts": attempt_number,
                        "next_attempt_at": next_attempt_at,
                    },
                )
                return
            await mark_audit_export_dead_letter(
                export_id,
                attempts=attempt_number,
                last_error=error_text,
                completed_at=_now_iso(),
            )
            logger.error(
                "export.dead_letter",
                extra={
                    "component": "worker",
                    "export_id": export_id,
                    "attempts": attempt_number,
                    "last_error": error_text,
                },
            )

    async def _build_export_content(
        self,
        *,
        export_format: str,
        packet: dict[str, Any],
    ) -> tuple[bytes, str, str, str]:
        if export_format in {"csv", "pdf"}:
            content, sha256 = build_export_bytes(export_format, packet)
            content_type = (
                "text/csv; charset=utf-8" if export_format == "csv" else "application/pdf"
            )
            return content, sha256, export_format, content_type

        if export_format == "zip":
            pdf_bytes = build_pdf(packet)
            csv_bytes = build_csv(packet)
            evidence_items = await self._collect_evidence_items(packet)
            content = build_zip(packet, pdf_bytes, csv_bytes, evidence_items)
            sha256 = hashlib.sha256(content).hexdigest()
            return content, sha256, "zip", "application/zip"

        raise ValueError("Unsupported export format")

    async def _collect_evidence_items(self, packet: dict[str, Any]) -> list[dict[str, Any]]:
        settings = get_settings()
        evidence_files_raw = packet.get("evidence_files")
        normalized_rows: list[dict[str, Any]] = []
        if isinstance(evidence_files_raw, list):
            for item in evidence_files_raw:
                if not isinstance(item, dict):
                    continue
                storage_path = str(item.get("storage_path") or "").strip()
                if not storage_path:
                    continue
                normalized_rows.append(
                    {
                        "evidence_id": str(item.get("id") or "").strip(),
                        "task_id": str(item.get("task_id") or "").strip(),
                        "path": storage_path,
                        "filename": str(item.get("filename") or "").strip(),
                        "storage_bucket": str(item.get("storage_bucket") or "").strip(),
                    }
                )

        if not normalized_rows:
            legacy_rows = packet.get("task_evidence")
            if isinstance(legacy_rows, list):
                for item in legacy_rows:
                    if not isinstance(item, dict):
                        continue
                    evidence_type = str(item.get("type") or "").strip().lower()
                    evidence_path = str(item.get("ref") or "").strip()
                    if evidence_type != "file" or not evidence_path:
                        continue
                    normalized_rows.append(
                        {
                            "evidence_id": str(item.get("id") or "").strip(),
                            "task_id": str(item.get("task_id") or "").strip(),
                            "path": evidence_path,
                            "filename": evidence_path.rsplit("/", 1)[-1],
                            "storage_bucket": settings.EVIDENCE_BUCKET_NAME,
                        }
                    )

        if not normalized_rows:
            return []

        max_files = settings.AUDIT_PACKET_MAX_EVIDENCE_FILES
        max_total_bytes = settings.AUDIT_PACKET_MAX_TOTAL_BYTES
        total_evidence_bytes = 0
        included_files = 0
        total_limit_reached = False
        evidence_items: list[dict[str, Any]] = []

        for item in normalized_rows:
            evidence_path = str(item.get("path") or "").strip()
            evidence_id = str(item.get("evidence_id") or "").strip()
            task_id = str(item.get("task_id") or "").strip()
            storage_bucket = str(item.get("storage_bucket") or "").strip() or settings.EVIDENCE_BUCKET_NAME
            evidence_record: dict[str, Any] = {
                "evidence_id": evidence_id or None,
                "task_id": task_id or None,
                "path": evidence_path or None,
                "filename": str(item.get("filename") or "").strip() or evidence_path.rsplit("/", 1)[-1],
            }

            if total_limit_reached:
                evidence_record["skipped"] = True
                evidence_record["reason"] = "max total evidence bytes reached"
                evidence_items.append(evidence_record)
                continue

            if included_files >= max_files:
                evidence_record["skipped"] = True
                evidence_record["reason"] = "max evidence file count reached"
                evidence_items.append(evidence_record)
                continue

            try:
                file_bytes = await download_bytes(storage_bucket, evidence_path)
            except HTTPException as exc:
                detail = _safe_text(exc.detail).lower()
                if exc.status_code in {400, 404, 413} or (exc.status_code == 502 and "bucket" in detail):
                    evidence_record["skipped"] = True
                    evidence_record["reason"] = _safe_text(exc.detail) or "evidence unavailable"
                    evidence_items.append(evidence_record)
                    logger.warning(
                        "export.evidence_skipped",
                        extra={
                            "component": "worker",
                            "evidence_id": evidence_id or None,
                            "task_id": task_id or None,
                            "reason": evidence_record["reason"],
                        },
                    )
                    continue
                raise

            if total_evidence_bytes + len(file_bytes) > max_total_bytes:
                evidence_record["skipped"] = True
                evidence_record["reason"] = "max total evidence bytes reached"
                evidence_items.append(evidence_record)
                total_limit_reached = True
                continue

            evidence_record["bytes"] = file_bytes
            evidence_items.append(evidence_record)
            included_files += 1
            total_evidence_bytes += len(file_bytes)

        return evidence_items
