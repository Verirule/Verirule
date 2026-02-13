from __future__ import annotations

from typing import Any

from app.core.supabase_rest import (
    list_controls,
    list_finding_controls,
    select_latest_finding_explanation,
    select_source_by_id,
)
from app.services.control_suggest import suggest_controls_for_finding

_SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def normalize_alert_task_rules(row: dict[str, Any] | None) -> dict[str, Any]:
    rules = row if isinstance(row, dict) else {}
    min_severity = str(rules.get("min_severity") or "medium").strip().lower()
    if min_severity not in {"low", "medium", "high"}:
        min_severity = "medium"

    return {
        "enabled": bool(rules.get("enabled", True)),
        "auto_create_task_on_alert": bool(rules.get("auto_create_task_on_alert", True)),
        "min_severity": min_severity,
        "auto_link_suggested_controls": bool(rules.get("auto_link_suggested_controls", True)),
        "auto_add_evidence_checklist": bool(rules.get("auto_add_evidence_checklist", True)),
    }


def severity_meets_minimum(severity: str | None, min_severity: str) -> bool:
    normalized_severity = str(severity or "medium").strip().lower()
    normalized_min = str(min_severity or "medium").strip().lower()
    severity_rank = _SEVERITY_ORDER.get(normalized_severity, _SEVERITY_ORDER["medium"])
    min_rank = _SEVERITY_ORDER.get(normalized_min, _SEVERITY_ORDER["medium"])
    return severity_rank >= min_rank


def build_task_title(finding: dict[str, Any] | None) -> str:
    summary = str((finding or {}).get("summary") or "").strip()
    title = str((finding or {}).get("title") or "").strip()
    base = summary or title or "Finding update"
    return f"{base} - remediation"[:120]


def build_task_description(finding: dict[str, Any] | None) -> str:
    finding_row = finding if isinstance(finding, dict) else {}
    summary = str(finding_row.get("summary") or "").strip()
    raw_url = str(finding_row.get("raw_url") or "").strip()

    details: list[str] = []
    if summary:
        details.append(f"What changed: {summary}")
    if raw_url:
        details.append(f"Source: {raw_url}")
    if not details:
        details.append("Investigate this alert and complete remediation evidence.")
    return "\n".join(details)[:4000]


def checklist_evidence_items(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for row in rows:
        required = row.get("required")
        if required is False:
            continue

        control_id = str(row.get("control_id") or "").strip()
        label = str(row.get("label") or "").strip()
        description = str(row.get("description") or "").strip()
        evidence_type = str(row.get("evidence_type") or "").strip()
        if not label:
            continue

        dedupe_key = (control_id, label.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        ref_text = f"[pending] {label}"
        if description:
            ref_text = f"{ref_text}: {description}"
        if evidence_type:
            ref_text = f"{ref_text} ({evidence_type})"
        entries.append({"type": "log", "ref": ref_text[:4096]})

    return entries


async def resolve_control_ids_for_alert(
    access_token: str,
    *,
    org_id: str,
    finding_id: str,
    finding_row: dict[str, Any] | None,
    allow_suggestions: bool,
    suggestion_limit: int = 3,
) -> list[str]:
    linked_rows = await list_finding_controls(access_token, org_id, finding_id)
    linked_control_ids = [
        str(row.get("control_id")).strip()
        for row in linked_rows
        if isinstance(row.get("control_id"), str) and str(row.get("control_id")).strip()
    ]
    if linked_control_ids:
        return list(dict.fromkeys(linked_control_ids))
    if not allow_suggestions:
        return []

    source_tags: list[str] = []
    source_id = (finding_row or {}).get("source_id")
    if isinstance(source_id, str) and source_id.strip():
        source = await select_source_by_id(access_token, source_id.strip())
        tags = source.get("tags") if isinstance(source, dict) else None
        if isinstance(tags, list):
            source_tags = [str(tag) for tag in tags if isinstance(tag, str)]

    suggestions = suggest_controls_for_finding(
        finding=finding_row or {},
        explanation=await select_latest_finding_explanation(access_token, finding_id),
        template_tags=source_tags,
        control_catalog=await list_controls(access_token),
    )
    suggested_control_ids = [
        str(item.get("control_id")).strip()
        for item in suggestions
        if isinstance(item.get("control_id"), str) and str(item.get("control_id")).strip()
    ]
    return list(dict.fromkeys(suggested_control_ids))[:suggestion_limit]
