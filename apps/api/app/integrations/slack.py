from typing import Any

import httpx
from fastapi import HTTPException, status

from app.integrations.models import AlertNotification


class SlackWebhookConnector:
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send_test_message(self, text: str) -> None:
        await self._post_payload({"text": text})

    async def send_alert(self, alert: AlertNotification) -> None:
        lines = [
            f":rotating_light: *New alert* ({alert.severity.upper()})",
            f"*Finding*: {alert.title}",
            f"*Summary*: {alert.summary}",
            f"*Alert ID*: `{alert.alert_id}`",
            f"*Org ID*: `{alert.org_id}`",
        ]
        await self._post_payload({"text": "\n".join(lines)})

    async def _post_payload(self, payload: dict[str, Any]) -> None:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to send Slack webhook request.",
            ) from exc
