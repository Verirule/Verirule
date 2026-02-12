from __future__ import annotations

import csv
import hashlib
from collections import Counter, defaultdict
from datetime import UTC, datetime
from io import BytesIO, StringIO
from pathlib import PurePosixPath
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PDF_TOP_FINDINGS = 30
PDF_TOP_ALERTS = 50
PDF_TOP_TASKS = 60
PDF_TOP_RUNS = 60
PDF_TOP_AUDIT_EVENTS = 100


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


def _sort_rows(rows: list[dict[str, Any]], *, timestamp_field: str) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            _safe_text(row.get(timestamp_field)),
            _safe_text(row.get("id")),
        ),
        reverse=True,
    )


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _filename_only(value: str) -> str:
    if not value:
        return ""
    return PurePosixPath(value).name


def build_csv(packet: dict[str, Any]) -> bytes:
    findings = _sort_rows(_to_rows(packet.get("findings")), timestamp_field="detected_at")
    alerts = _sort_rows(_to_rows(packet.get("alerts")), timestamp_field="created_at")
    tasks = _sort_rows(_to_rows(packet.get("tasks")), timestamp_field="created_at")
    evidence_rows = _sort_rows(_to_rows(packet.get("task_evidence")), timestamp_field="created_at")
    runs = _sort_rows(_to_rows(packet.get("runs")), timestamp_field="created_at")
    snapshots = _sort_rows(_to_rows(packet.get("snapshots")), timestamp_field="fetched_at")
    timeline = _sort_rows(_to_rows(packet.get("audit_timeline")), timestamp_field="created_at")
    explanations = _to_rows(packet.get("finding_explanations"))

    explanation_finding_ids = {
        _safe_text(row.get("finding_id")) for row in explanations if _safe_text(row.get("finding_id"))
    }
    task_ids_by_alert: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        alert_id = _safe_text(task.get("alert_id"))
        if alert_id:
            task_ids_by_alert[alert_id].append(_safe_text(task.get("id")))

    snapshot_count_by_source = Counter(_safe_text(row.get("source_id")) for row in snapshots)
    snapshot_count_by_source.pop("", None)

    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "type",
            "id",
            "created_at",
            "severity_or_status",
            "title_or_summary",
            "related_ids",
        ]
    )

    for finding in findings:
        finding_id = _safe_text(finding.get("id"))
        related = "|".join(
            [
                f"source:{_safe_text(finding.get('source_id'))}",
                f"run:{_safe_text(finding.get('run_id'))}",
                f"has_explanation:{finding_id in explanation_finding_ids}",
            ]
        )
        writer.writerow(
            [
                "finding",
                finding_id,
                _safe_text(finding.get("detected_at")),
                _safe_text(finding.get("severity")),
                _safe_text(finding.get("title")) or _safe_text(finding.get("summary")),
                related,
            ]
        )

    for alert in alerts:
        alert_id = _safe_text(alert.get("id"))
        linked_task_ids = ",".join(sorted(task_ids_by_alert.get(alert_id, [])))
        writer.writerow(
            [
                "alert",
                alert_id,
                _safe_text(alert.get("created_at")),
                _safe_text(alert.get("status")),
                f"finding:{_safe_text(alert.get('finding_id'))}",
                f"tasks:{linked_task_ids}",
            ]
        )

    for task in tasks:
        writer.writerow(
            [
                "task",
                _safe_text(task.get("id")),
                _safe_text(task.get("created_at")),
                _safe_text(task.get("status")),
                _safe_text(task.get("title")),
                "|".join(
                    [
                        f"alert:{_safe_text(task.get('alert_id'))}",
                        f"finding:{_safe_text(task.get('finding_id'))}",
                    ]
                ),
            ]
        )

    for evidence in evidence_rows:
        ref = _safe_text(evidence.get("ref"))
        if _safe_text(evidence.get("type")) == "file":
            ref = _filename_only(ref)
        writer.writerow(
            [
                "evidence",
                _safe_text(evidence.get("id")),
                _safe_text(evidence.get("created_at")),
                _safe_text(evidence.get("type")),
                ref,
                f"task:{_safe_text(evidence.get('task_id'))}",
            ]
        )

    for run in runs:
        writer.writerow(
            [
                "run",
                _safe_text(run.get("id")),
                _safe_text(run.get("created_at")),
                _safe_text(run.get("status")),
                f"source:{_safe_text(run.get('source_id'))}",
                "",
            ]
        )

    writer.writerow(
        [
            "snapshot_summary",
            "total",
            _iso_now(),
            str(len(snapshots)),
            "Total snapshots in range",
            "",
        ]
    )
    for source_id, count in sorted(snapshot_count_by_source.items()):
        writer.writerow(
            [
                "snapshot_summary",
                source_id,
                _iso_now(),
                str(count),
                "Snapshots by source",
                "",
            ]
        )

    for event in timeline:
        writer.writerow(
            [
                "audit_timeline",
                _safe_text(event.get("id")),
                _safe_text(event.get("created_at")),
                _safe_text(event.get("action")),
                _safe_text(event.get("entity_type")),
                _safe_text(event.get("entity_id")),
            ]
        )

    return buffer.getvalue().encode("utf-8")


def _build_table(rows: list[list[str]], column_widths: list[float]) -> Table:
    table = Table(rows, colWidths=column_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f4f7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_pdf(packet: dict[str, Any]) -> bytes:
    findings = _sort_rows(_to_rows(packet.get("findings")), timestamp_field="detected_at")
    alerts = _sort_rows(_to_rows(packet.get("alerts")), timestamp_field="created_at")
    tasks = _sort_rows(_to_rows(packet.get("tasks")), timestamp_field="created_at")
    evidence_rows = _sort_rows(_to_rows(packet.get("task_evidence")), timestamp_field="created_at")
    runs = _sort_rows(_to_rows(packet.get("runs")), timestamp_field="created_at")
    snapshots = _sort_rows(_to_rows(packet.get("snapshots")), timestamp_field="fetched_at")
    timeline = _sort_rows(_to_rows(packet.get("audit_timeline")), timestamp_field="created_at")
    explanations = _to_rows(packet.get("finding_explanations"))

    explanation_finding_ids = {
        _safe_text(row.get("finding_id")) for row in explanations if _safe_text(row.get("finding_id"))
    }
    tasks_by_alert: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        alert_id = _safe_text(task.get("alert_id"))
        if alert_id:
            tasks_by_alert[alert_id].append(_safe_text(task.get("id")))

    evidence_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for evidence in evidence_rows:
        task_id = _safe_text(evidence.get("task_id"))
        if task_id:
            evidence_by_task[task_id].append(evidence)

    snapshot_count_by_source = Counter(_safe_text(row.get("source_id")) for row in snapshots)
    snapshot_count_by_source.pop("", None)

    source_ids = {
        _safe_text(row.get("source_id"))
        for row in [*findings, *runs, *snapshots]
        if _safe_text(row.get("source_id"))
    }
    alerts_open = sum(1 for alert in alerts if _safe_text(alert.get("status")) == "open")
    alerts_resolved = sum(1 for alert in alerts if _safe_text(alert.get("status")) == "resolved")
    tasks_open = sum(1 for task in tasks if _safe_text(task.get("status")) != "done")
    tasks_done = sum(1 for task in tasks if _safe_text(task.get("status")) == "done")

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ExportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#111827"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ExportHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#111827"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ExportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#1f2937"),
        )
    )

    org_id = _safe_text(packet.get("org_id"))
    export_id = _safe_text(packet.get("export_id"))
    from_ts = _safe_text(packet.get("from")) or "not set"
    to_ts = _safe_text(packet.get("to")) or "not set"
    generated_at = _safe_text(packet.get("generated_at")) or _iso_now()

    story: list[Any] = []
    story.append(Paragraph("Audit Export Report", styles["ExportTitle"]))
    story.append(Paragraph(f"Organization: {org_id}", styles["ExportBody"]))
    story.append(Paragraph(f"Export ID: {export_id}", styles["ExportBody"]))
    story.append(Paragraph(f"Date range: {from_ts} to {to_ts}", styles["ExportBody"]))
    story.append(Paragraph(f"Generated at: {generated_at}", styles["ExportBody"]))
    story.append(Spacer(1, 0.28 * inch))

    story.append(Paragraph("A) Executive Summary", styles["ExportHeading"]))
    summary_rows = [
        ["Metric", "Value"],
        ["Sources in scope", str(len(source_ids))],
        ["Findings", str(len(findings))],
        ["Alerts open", str(alerts_open)],
        ["Alerts resolved", str(alerts_resolved)],
        ["Tasks open", str(tasks_open)],
        ["Tasks done", str(tasks_done)],
        ["Monitoring runs", str(len(runs))],
        ["Snapshots", str(len(snapshots))],
        ["Audit events", str(len(timeline))],
    ]
    story.append(_build_table(summary_rows, [2.8 * inch, 3.7 * inch]))
    story.append(Spacer(1, 0.12 * inch))

    snapshot_rows = [["Source", "Snapshot count"]]
    for source_id, count in sorted(snapshot_count_by_source.items()):
        snapshot_rows.append([source_id, str(count)])
    if len(snapshot_rows) == 1:
        snapshot_rows.append(["No snapshots in range", "0"])
    story.append(Paragraph("Snapshots summary", styles["ExportBody"]))
    story.append(_build_table(snapshot_rows[:26], [4.6 * inch, 1.9 * inch]))

    story.append(PageBreak())
    story.append(Paragraph("B) Findings", styles["ExportHeading"]))
    if not findings:
        story.append(Paragraph("No findings in the selected date range.", styles["ExportBody"]))
    else:
        finding_rows = [["Detected", "Severity", "Title", "Details"]]
        for finding in findings[:PDF_TOP_FINDINGS]:
            finding_id = _safe_text(finding.get("id"))
            details = (
                f"raw_url={_safe_text(finding.get('raw_url')) or 'n/a'}; "
                f"has_explanation={finding_id in explanation_finding_ids}; "
                f"summary={_safe_text(finding.get('summary'))[:180]}"
            )
            finding_rows.append(
                [
                    _safe_text(finding.get("detected_at")),
                    _safe_text(finding.get("severity")),
                    _safe_text(finding.get("title"))[:80],
                    details,
                ]
            )
        story.append(
            _build_table(
                finding_rows,
                [1.4 * inch, 0.9 * inch, 1.6 * inch, 2.6 * inch],
            )
        )

    story.append(Spacer(1, 0.14 * inch))
    story.append(Paragraph("C) Alerts", styles["ExportHeading"]))
    if not alerts:
        story.append(Paragraph("No alerts in the selected date range.", styles["ExportBody"]))
    else:
        alert_rows = [["Created", "Status", "Finding", "Linked tasks"]]
        for alert in alerts[:PDF_TOP_ALERTS]:
            alert_id = _safe_text(alert.get("id"))
            linked = ", ".join(sorted(tasks_by_alert.get(alert_id, []))) or "-"
            alert_rows.append(
                [
                    _safe_text(alert.get("created_at")),
                    _safe_text(alert.get("status")),
                    _safe_text(alert.get("finding_id")),
                    linked,
                ]
            )
        story.append(_build_table(alert_rows, [1.5 * inch, 1.0 * inch, 2.0 * inch, 2.4 * inch]))

    story.append(PageBreak())
    story.append(Paragraph("D) Tasks and Evidence", styles["ExportHeading"]))
    if not tasks:
        story.append(Paragraph("No tasks in the selected date range.", styles["ExportBody"]))
    else:
        for task in tasks[:PDF_TOP_TASKS]:
            task_id = _safe_text(task.get("id"))
            story.append(
                Paragraph(
                    (
                        f"Task {task_id}: {_safe_text(task.get('title'))} "
                        f"(status={_safe_text(task.get('status'))}, created={_safe_text(task.get('created_at'))})"
                    ),
                    styles["ExportBody"],
                )
            )
            task_evidence = evidence_by_task.get(task_id, [])
            if not task_evidence:
                story.append(Paragraph("Evidence: none", styles["ExportBody"]))
            else:
                refs: list[str] = []
                for evidence in task_evidence[:10]:
                    evidence_ref = _safe_text(evidence.get("ref"))
                    if _safe_text(evidence.get("type")) == "file":
                        evidence_ref = _filename_only(evidence_ref)
                    refs.append(f"{_safe_text(evidence.get('type'))}:{evidence_ref}")
                story.append(Paragraph(f"Evidence: {', '.join(refs)}", styles["ExportBody"]))
            story.append(Spacer(1, 0.06 * inch))

    story.append(Spacer(1, 0.14 * inch))
    story.append(Paragraph("E) Monitoring Runs", styles["ExportHeading"]))
    if not runs:
        story.append(Paragraph("No monitoring runs in the selected date range.", styles["ExportBody"]))
    else:
        run_rows = [["Created", "Status", "Source", "Started / Finished"]]
        for run in runs[:PDF_TOP_RUNS]:
            run_rows.append(
                [
                    _safe_text(run.get("created_at")),
                    _safe_text(run.get("status")),
                    _safe_text(run.get("source_id")),
                    f"{_safe_text(run.get('started_at'))} / {_safe_text(run.get('finished_at'))}",
                ]
            )
        story.append(_build_table(run_rows, [1.5 * inch, 1.0 * inch, 2.2 * inch, 2.2 * inch]))

    story.append(PageBreak())
    story.append(Paragraph("F) Audit Timeline", styles["ExportHeading"]))
    if not timeline:
        story.append(Paragraph("No audit timeline events in the selected date range.", styles["ExportBody"]))
    else:
        audit_rows = [["At", "Action", "Entity", "Metadata summary"]]
        for event in timeline[:PDF_TOP_AUDIT_EVENTS]:
            metadata_value = event.get("metadata")
            metadata_summary = ""
            if isinstance(metadata_value, dict):
                keys = sorted(metadata_value.keys())[:6]
                metadata_summary = ", ".join(keys)
            audit_rows.append(
                [
                    _safe_text(event.get("created_at")),
                    _safe_text(event.get("action")),
                    f"{_safe_text(event.get('entity_type'))}:{_safe_text(event.get('entity_id'))}",
                    metadata_summary,
                ]
            )
        story.append(_build_table(audit_rows, [1.4 * inch, 1.5 * inch, 2.2 * inch, 1.8 * inch]))

    out = BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=LETTER,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Audit Export Report",
        author="Verirule",
    )
    doc.build(story)
    return out.getvalue()


def build_export_bytes(export_format: str, packet: dict[str, Any]) -> tuple[bytes, str]:
    if export_format == "csv":
        content = build_csv(packet)
    elif export_format == "pdf":
        content = build_pdf(packet)
    else:
        raise ValueError("Unsupported export format")

    sha256 = hashlib.sha256(content).hexdigest()
    return content, sha256
