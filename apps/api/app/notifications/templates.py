from __future__ import annotations

from typing import Any


def digest_email(
    org_name: str,
    alerts: list[dict[str, Any]],
    findings: dict[str, int],
    readiness_summary: dict[str, Any],
    dashboard_url: str,
) -> dict[str, str]:
    org_label = org_name.strip() or "your workspace"
    open_alerts = int(findings.get("open_alerts", 0))
    findings_total = int(findings.get("findings_total", 0))
    readiness_score = readiness_summary.get("score")
    dashboard_link = dashboard_url.strip()

    top_lines = []
    for alert in alerts[:5]:
        severity = str(alert.get("severity") or "medium").upper()
        title = str(alert.get("title") or "Untitled finding")
        top_lines.append(f"- [{severity}] {title}")

    alerts_section = "\n".join(top_lines) if top_lines else "- No open alerts matched your configured threshold."
    readiness_line = f"Readiness score: {readiness_score}/100" if isinstance(readiness_score, int) else "Readiness score: unavailable"

    subject = f"Verirule digest: {org_label}"
    text = "\n".join(
        [
            f"Daily digest for {org_label}",
            "",
            f"Open alerts: {open_alerts}",
            f"Findings captured: {findings_total}",
            readiness_line,
            "",
            "Top alerts:",
            alerts_section,
            "",
            f"Dashboard: {dashboard_link}" if dashboard_link else "Dashboard: /dashboard",
            "",
            "This message is informational and does not replace legal or compliance advice.",
        ]
    )

    html_alerts = "".join(f"<li>{line[2:]}</li>" for line in top_lines) or (
        "<li>No open alerts matched your configured threshold.</li>"
    )
    dashboard_link = (
        f'<a href="{dashboard_link}">{dashboard_link}</a>'
        if dashboard_link
        else '<a href="/dashboard">/dashboard</a>'
    )
    readiness_html = (
        f"Readiness score: <strong>{readiness_score}/100</strong>"
        if isinstance(readiness_score, int)
        else "Readiness score: <strong>unavailable</strong>"
    )
    html = (
        "<html><body>"
        f"<p>Daily digest for <strong>{org_label}</strong></p>"
        f"<p>Open alerts: <strong>{open_alerts}</strong><br/>"
        f"Findings captured: <strong>{findings_total}</strong><br/>{readiness_html}</p>"
        "<p>Top alerts:</p>"
        f"<ul>{html_alerts}</ul>"
        f"<p>Dashboard: {dashboard_link}</p>"
        "<p>This message is informational and does not replace legal or compliance advice.</p>"
        "</body></html>"
    )

    return {"subject": subject, "html": html, "text": text}


def immediate_alert_email(
    org_name: str,
    alert: dict[str, Any],
    dashboard_url: str,
) -> dict[str, str]:
    org_label = org_name.strip() or "your workspace"
    severity = str(alert.get("severity") or "high").upper()
    title = str(alert.get("title") or "Untitled finding")
    dashboard_link = dashboard_url.strip()

    subject = f"Verirule alert ({severity}): {org_label}"
    text = "\n".join(
        [
            f"Immediate alert for {org_label}",
            "",
            f"Severity: {severity}",
            f"Title: {title}",
            "",
            f"Dashboard: {dashboard_link}" if dashboard_link else "Dashboard: /dashboard",
            "",
            "Please review this alert promptly.",
        ]
    )
    dashboard_html = (
        f"<p>Dashboard: <a href=\"{dashboard_link}\">{dashboard_link}</a></p>"
        if dashboard_link
        else "<p>Dashboard: /dashboard</p>"
    )
    html = (
        "<html><body>"
        f"<p>Immediate alert for <strong>{org_label}</strong></p>"
        f"<p>Severity: <strong>{severity}</strong><br/>Title: {title}</p>"
        f"{dashboard_html}"
        "<p>Please review this alert promptly.</p>"
        "</body></html>"
    )
    return {"subject": subject, "html": html, "text": text}
