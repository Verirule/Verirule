from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException

from app.core.settings import get_settings
from app.core.supabase_rest import (
    select_audit_packet_data,
    select_queued_audit_exports_service,
    update_audit_export_status,
)
from app.core.supabase_storage_admin import download_bytes, upload_bytes
from app.exports.generate import build_csv, build_export_bytes, build_pdf
from app.exports.packet import build_zip

EXPORT_BATCH_LIMIT = 3


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
    if isinstance(exc, HTTPException) and isinstance(exc.detail, str) and exc.detail.strip():
        return exc.detail.strip()[:1000]
    message = str(exc).strip()
    if not message:
        message = "Export generation failed."
    return message[:1000]


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
        "evidence": "task_evidence",
        "comments": "task_comments",
        "runs": "runs",
        "snapshots": "snapshots",
        "timeline": "audit_timeline",
        "audit_timeline": "audit_timeline",
    }
    selected = {aliases[item] for item in include if item in aliases}
    list_keys = {
        "findings",
        "alerts",
        "tasks",
        "task_evidence",
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


class ExportProcessor:
    def __init__(self, *, access_token: str, bucket_name: str) -> None:
        self.access_token = access_token
        self.bucket_name = bucket_name

    async def process_queued_exports_once(self, limit: int = EXPORT_BATCH_LIMIT) -> int:
        export_rows = await select_queued_audit_exports_service(limit=limit)
        for row in export_rows:
            await self._process_single_export(row)
        return len(export_rows)

    async def _process_single_export(self, row: dict[str, Any]) -> None:
        export_id = str(row.get("id") or "")
        org_id = str(row.get("org_id") or "")
        export_format = str(row.get("format") or "").lower()
        scope = row.get("scope") if isinstance(row.get("scope"), dict) else {}
        include = _scope_include(scope)

        if not export_id or not org_id or export_format not in {"csv", "pdf", "zip"}:
            return

        await update_audit_export_status(
            export_id,
            status_value="running",
            file_path=None,
            file_sha256=None,
            error_text=None,
            completed_at=None,
        )

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
            await update_audit_export_status(
                export_id,
                status_value="failed",
                file_path=None,
                file_sha256=None,
                error_text=_sanitize_error_text(exc),
                completed_at=_now_iso(),
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
        evidence_rows = packet.get("task_evidence")
        if not isinstance(evidence_rows, list):
            return []

        max_files = settings.AUDIT_PACKET_MAX_EVIDENCE_FILES
        max_total_bytes = settings.AUDIT_PACKET_MAX_TOTAL_BYTES
        total_evidence_bytes = 0
        included_files = 0
        total_limit_reached = False
        evidence_items: list[dict[str, Any]] = []

        for item in evidence_rows:
            if not isinstance(item, dict):
                continue

            evidence_type = str(item.get("type") or "").strip().lower()
            evidence_path = str(item.get("ref") or "").strip()
            evidence_id = str(item.get("id") or "").strip()
            task_id = str(item.get("task_id") or "").strip()
            evidence_record: dict[str, Any] = {
                "evidence_id": evidence_id or None,
                "task_id": task_id or None,
                "path": evidence_path or None,
            }

            if evidence_type != "file" or not evidence_path:
                continue

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
                file_bytes = await download_bytes(settings.EVIDENCE_BUCKET_NAME, evidence_path)
            except HTTPException as exc:
                if exc.status_code in {
                    400,
                    404,
                    413,
                }:
                    evidence_record["skipped"] = True
                    evidence_record["reason"] = _safe_text(exc.detail) or "evidence unavailable"
                    evidence_items.append(evidence_record)
                    continue
                raise

            if total_evidence_bytes + len(file_bytes) > max_total_bytes:
                evidence_record["skipped"] = True
                evidence_record["reason"] = "max total evidence bytes reached"
                evidence_items.append(evidence_record)
                total_limit_reached = True
                continue

            evidence_record["filename"] = evidence_path.rsplit("/", 1)[-1]
            evidence_record["bytes"] = file_bytes
            evidence_items.append(evidence_record)
            included_files += 1
            total_evidence_bytes += len(file_bytes)

        return evidence_items


def _safe_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


async def run_export_worker_loop() -> None:
    settings = get_settings()
    service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
    if not service_role_key:
        print("export worker disabled: SUPABASE_SERVICE_ROLE_KEY is not configured")
        while True:
            await asyncio.sleep(max(1, settings.WORKER_POLL_INTERVAL_SECONDS))

    processor = ExportProcessor(
        access_token=service_role_key,
        bucket_name=settings.EXPORTS_BUCKET_NAME,
    )

    while True:
        try:
            processed = await processor.process_queued_exports_once(limit=EXPORT_BATCH_LIMIT)
        except Exception as exc:  # pragma: no cover - loop resiliency
            print(f"export worker loop error: {exc}")
            await asyncio.sleep(max(1, settings.WORKER_POLL_INTERVAL_SECONDS))
            continue

        if processed == 0:
            await asyncio.sleep(max(1, settings.WORKER_POLL_INTERVAL_SECONDS))
