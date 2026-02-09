from fastapi import HTTPException, status

from app.integrations.models import IntegrationType
from app.integrations.slack import SlackWebhookConnector


def create_connector(integration_type: IntegrationType, webhook_url: str) -> SlackWebhookConnector:
    if integration_type == "slack":
        return SlackWebhookConnector(webhook_url)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported integration type: {integration_type}",
    )
