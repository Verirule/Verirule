from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.integrations import IntegrationOut, SlackConnectIn, SlackTestIn
from app.core.integration_crypto import decrypt_integration_secret, encrypt_integration_secret
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import rpc_upsert_integration, select_integration, select_integrations
from app.integrations.registry import create_connector

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/integrations")
async def integrations(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[IntegrationOut]]:
    rows = await select_integrations(auth.access_token, str(org_id))
    sanitized: list[IntegrationOut] = []
    for row in rows:
        config = row.get("config")
        has_secret = isinstance(config, dict) and isinstance(config.get("webhook_encrypted"), str)
        sanitized.append(
            IntegrationOut.model_validate(
                {
                    "id": row.get("id"),
                    "org_id": row.get("org_id"),
                    "type": row.get("type"),
                    "status": row.get("status"),
                    "has_secret": has_secret,
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
            )
        )
    return {"integrations": sanitized}


@router.post("/integrations/slack")
async def connect_slack(
    payload: SlackConnectIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    encrypted_webhook = encrypt_integration_secret(payload.webhook_url.strip())
    await rpc_upsert_integration(
        auth.access_token,
        {
            "p_org_id": str(payload.org_id),
            "p_type": "slack",
            "p_status": payload.status,
            "p_config": {"webhook_encrypted": encrypted_webhook},
        },
    )
    return {"ok": True}


@router.post("/integrations/slack/test")
async def test_slack(
    payload: SlackTestIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    row = await select_integration(auth.access_token, str(payload.org_id), "slack")
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slack integration is not configured for this organization.",
        )

    if row.get("status") != "enabled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slack integration is disabled for this organization.",
        )

    config = row.get("config")
    webhook_encrypted = config.get("webhook_encrypted") if isinstance(config, dict) else None
    if not isinstance(webhook_encrypted, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slack webhook is not configured for this organization.",
        )

    webhook_url = decrypt_integration_secret(webhook_encrypted)
    connector = create_connector("slack", webhook_url)
    await connector.send_test_message(payload.message or "Verirule Slack integration test message.")
    return {"ok": True}
