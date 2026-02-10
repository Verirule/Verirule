from typing import Any

import httpx
from fastapi import HTTPException, status


async def send_webhook(webhook_url: str, payload: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send Slack webhook request.",
        ) from exc


def build_alert_payload(
    *,
    org_id: str,
    alert_id: str,
    severity: str,
    title: str,
    summary: str,
    alert_link: str,
) -> dict[str, str]:
    text = (
        f"Verirule alert ({severity.upper()})\n"
        f"Org: {org_id}\n"
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Alert: {alert_link}\n"
        f"Alert ID: {alert_id}"
    )
    return {"text": text}
