from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any

FILENAME_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]")
MAX_SAFE_FILENAME_LEN = 120


def _safe_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_filename(value: object | None, fallback: str = "file") -> str:
    raw = _safe_text(value).replace("\\", "/").split("/")[-1].strip()
    if not raw:
        raw = fallback
    raw = FILENAME_SANITIZE_RE.sub("_", raw)
    raw = re.sub(r"_+", "_", raw).strip("._")
    if not raw:
        raw = fallback
    return raw[:MAX_SAFE_FILENAME_LEN]


def _safe_segment(value: object | None, fallback: str) -> str:
    candidate = _safe_filename(value, fallback=fallback)
    return candidate or fallback


def _packet_counts(packet: dict[str, Any]) -> dict[str, int]:
    return {
        "findings": len(_to_rows(packet.get("findings"))),
        "alerts": len(_to_rows(packet.get("alerts"))),
        "tasks": len(_to_rows(packet.get("tasks"))),
        "task_evidence": len(_to_rows(packet.get("task_evidence"))),
        "runs": len(_to_rows(packet.get("runs"))),
        "snapshots": len(_to_rows(packet.get("snapshots"))),
        "audit_timeline": len(_to_rows(packet.get("audit_timeline"))),
    }


def build_manifest(
    export_id: str,
    org_id: str,
    scope: dict[str, Any],
    generated_at: str,
    counts: dict[str, int],
    files: list[dict[str, Any]],
) -> bytes:
    total_bytes = 0
    file_count = 0
    skipped_count = 0
    warnings: list[str] = []

    for item in files:
        skipped = bool(item.get("skipped"))
        if skipped:
            skipped_count += 1
            reason = _safe_text(item.get("reason")) or "skipped"
            file_label = _safe_text(item.get("path")) or _safe_text(item.get("evidence_id")) or "unknown"
            warnings.append(f"{file_label}: {reason}")
            continue
        file_count += 1
        total_bytes += int(item.get("bytes") or 0)

    payload = {
        "export_id": export_id,
        "org_id": org_id,
        "scope": scope,
        "generated_at": generated_at,
        "totals": {
            **counts,
            "file_count": file_count,
            "skipped_files": skipped_count,
            "total_bytes": total_bytes,
        },
        "warnings": warnings,
        "files": files,
    }
    return json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")


def build_zip(
    packet: dict[str, Any],
    pdf_bytes: bytes,
    csv_bytes: bytes,
    evidence_items: list[dict[str, Any]],
) -> bytes:
    export_id = _safe_text(packet.get("export_id"))
    org_id = _safe_text(packet.get("org_id"))
    generated_at = _safe_text(packet.get("generated_at")) or _now_iso()
    scope = {
        "from": packet.get("from"),
        "to": packet.get("to"),
        "include": packet.get("include"),
    }

    files: list[dict[str, Any]] = []
    output = BytesIO()

    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("audit_report.pdf", pdf_bytes)
        files.append(
            {
                "path": "audit_report.pdf",
                "sha256": _sha256_bytes(pdf_bytes),
                "bytes": len(pdf_bytes),
                "source": "generated",
            }
        )

        archive.writestr("audit_data.csv", csv_bytes)
        files.append(
            {
                "path": "audit_data.csv",
                "sha256": _sha256_bytes(csv_bytes),
                "bytes": len(csv_bytes),
                "source": "generated",
            }
        )

        for evidence in evidence_items:
            evidence_id = _safe_text(evidence.get("evidence_id"))
            task_id = _safe_text(evidence.get("task_id"))
            source_path = _safe_text(evidence.get("path"))
            fallback_name = (
                PurePosixPath(source_path).name if source_path else f"{evidence_id or 'evidence'}.bin"
            )
            safe_name = _safe_filename(
                evidence.get("filename") or source_path or fallback_name,
                fallback=fallback_name,
            )
            safe_evidence_id = _safe_segment(evidence_id, fallback="evidence")

            if task_id:
                safe_task_id = _safe_segment(task_id, fallback="task")
                evidence_zip_path = f"evidence/{safe_task_id}/{safe_evidence_id}-{safe_name}"
            else:
                evidence_zip_path = f"evidence/{safe_evidence_id}"

            if evidence.get("skipped"):
                files.append(
                    {
                        "path": evidence_zip_path,
                        "sha256": "",
                        "bytes": 0,
                        "source": "evidence",
                        "evidence_id": evidence_id or None,
                        "task_id": task_id or None,
                        "skipped": True,
                        "reason": _safe_text(evidence.get("reason")) or "skipped",
                    }
                )
                continue

            data = evidence.get("bytes")
            if not isinstance(data, bytes):
                files.append(
                    {
                        "path": evidence_zip_path,
                        "sha256": "",
                        "bytes": 0,
                        "source": "evidence",
                        "evidence_id": evidence_id or None,
                        "task_id": task_id or None,
                        "skipped": True,
                        "reason": "missing evidence bytes",
                    }
                )
                continue

            archive.writestr(evidence_zip_path, data)
            files.append(
                {
                    "path": evidence_zip_path,
                    "sha256": _sha256_bytes(data),
                    "bytes": len(data),
                    "source": "evidence",
                    "evidence_id": evidence_id or None,
                    "task_id": task_id or None,
                }
            )

        counts = _packet_counts(packet)
        counts["evidence_files_considered"] = len(evidence_items)
        manifest_bytes = build_manifest(
            export_id=export_id,
            org_id=org_id,
            scope=scope,
            generated_at=generated_at,
            counts=counts,
            files=files,
        )
        archive.writestr("manifest.json", manifest_bytes)

    return output.getvalue()
