from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.integrations import (
    IntegrationOut,
    JiraConnectIn,
    JiraCreateIssueOut,
    OrgIntegrationIn,
    SlackConnectIn,
    SlackNotifyIn,
)
from app.core.crypto import decrypt_json, encrypt_json
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    rpc_disable_integration,
    rpc_upsert_integration,
    select_alert_by_id,
    select_finding_by_id,
    select_org_billing,
    select_integration_secret,
    select_integrations,
)
from app.integrations.jira import create_issue, test_connection
from app.integrations.slack import build_alert_payload, send_webhook

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


def _as_clean_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stored integration {field_name} is invalid.",
        )
    return value.strip()


def _ensure_connected_secret(
    row: dict[str, Any] | None, integration_name: str
) -> tuple[dict[str, Any], str]:
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{integration_name} integration is not connected for this organization.",
        )
    if row.get("status") != "connected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{integration_name} integration is not connected for this organization.",
        )

    ciphertext = row.get("secret_ciphertext")
    if not isinstance(ciphertext, str) or not ciphertext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{integration_name} integration is not connected for this organization.",
        )
    return row, ciphertext


async def _fetch_alert_and_finding(access_token: str, org_id: str, alert_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    alert = await select_alert_by_id(access_token, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    if alert.get("org_id") != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")

    finding_id = alert.get("finding_id")
    if not isinstance(finding_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid alert response from Supabase.",
        )

    finding = await select_finding_by_id(access_token, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")
    if finding.get("org_id") != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")

    return alert, finding


async def _require_paid_plan(access_token: str, org_id: str) -> None:
    row = await select_org_billing(access_token, org_id)
    plan = row.get("plan") if isinstance(row, dict) else None
    if plan in {"pro", "business"}:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Upgrade required",
    )


@router.get("/integrations")
async def integrations(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[IntegrationOut]]:
    rows = await select_integrations(auth.access_token, str(org_id))
    return {
        "integrations": [
            IntegrationOut.model_validate(
                {
                    "id": row.get("id"),
                    "org_id": row.get("org_id"),
                    "type": row.get("type"),
                    "status": row.get("status"),
                    "config": row.get("config") if isinstance(row.get("config"), dict) else {},
                    "updated_at": row.get("updated_at"),
                }
            )
            for row in rows
        ]
    }


@router.post("/integrations/slack/connect")
async def connect_slack(
    payload: SlackConnectIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    await _require_paid_plan(auth.access_token, str(payload.org_id))
    ciphertext = encrypt_json({"webhook_url": payload.webhook_url.strip()})
    await rpc_upsert_integration(
        auth.access_token,
        {
            "p_org_id": str(payload.org_id),
            "p_type": "slack",
            "p_status": "connected",
            "p_config": {"channel_hint": ""},
            "p_secret_ciphertext": ciphertext,
        },
    )
    return {"ok": True}


@router.post("/integrations/jira/connect")
async def connect_jira(
    payload: JiraConnectIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    await _require_paid_plan(auth.access_token, str(payload.org_id))
    base_url = payload.base_url.strip().rstrip("/")
    email = payload.email.strip()
    api_token = payload.api_token.strip()
    project_key = payload.project_key.strip()

    ciphertext = encrypt_json(
        {
            "base_url": base_url,
            "email": email,
            "api_token": api_token,
            "project_key": project_key,
        }
    )
    await rpc_upsert_integration(
        auth.access_token,
        {
            "p_org_id": str(payload.org_id),
            "p_type": "jira",
            "p_status": "connected",
            "p_config": {"base_url": base_url, "project_key": project_key},
            "p_secret_ciphertext": ciphertext,
        },
    )
    return {"ok": True}


@router.post("/integrations/slack/test")
async def test_slack(
    payload: OrgIntegrationIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    await _require_paid_plan(auth.access_token, str(payload.org_id))
    row = await select_integration_secret(auth.access_token, str(payload.org_id), "slack")
    _, ciphertext = _ensure_connected_secret(row, "Slack")

    secret = decrypt_json(ciphertext)
    webhook_url = _as_clean_str(secret.get("webhook_url"), "webhook_url")
    await send_webhook(webhook_url, {"text": "Verirule Slack integration test message."})
    return {"ok": True}


@router.post("/integrations/jira/test")
async def test_jira(
    payload: OrgIntegrationIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    await _require_paid_plan(auth.access_token, str(payload.org_id))
    row = await select_integration_secret(auth.access_token, str(payload.org_id), "jira")
    _, ciphertext = _ensure_connected_secret(row, "Jira")

    secret = decrypt_json(ciphertext)
    base_url = _as_clean_str(secret.get("base_url"), "base_url")
    email = _as_clean_str(secret.get("email"), "email")
    api_token = _as_clean_str(secret.get("api_token"), "api_token")
    await test_connection(base_url, email, api_token)
    return {"ok": True}


@router.post("/integrations/slack/notify")
async def notify_slack(
    payload: SlackNotifyIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    await _require_paid_plan(auth.access_token, str(payload.org_id))
    row = await select_integration_secret(auth.access_token, str(payload.org_id), "slack")
    _, ciphertext = _ensure_connected_secret(row, "Slack")
    secret = decrypt_json(ciphertext)
    webhook_url = _as_clean_str(secret.get("webhook_url"), "webhook_url")

    alert, finding = await _fetch_alert_and_finding(auth.access_token, str(payload.org_id), str(payload.alert_id))
    severity = _as_clean_str(finding.get("severity"), "severity")
    title = _as_clean_str(finding.get("title"), "title")
    summary = _as_clean_str(finding.get("summary"), "summary")
    alert_row_id = _as_clean_str(alert.get("id"), "id")
    org_row_id = _as_clean_str(alert.get("org_id"), "org_id")
    alert_link = f"/dashboard/alerts/{alert_row_id}?org_id={org_row_id}"

    await send_webhook(
        webhook_url,
        build_alert_payload(
            org_id=org_row_id,
            alert_id=alert_row_id,
            severity=severity,
            title=title,
            summary=summary,
            alert_link=alert_link,
        ),
    )
    return {"ok": True}


@router.post("/integrations/jira/create-issue")
async def create_jira_issue(
    payload: SlackNotifyIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> JiraCreateIssueOut:
    await _require_paid_plan(auth.access_token, str(payload.org_id))
    row = await select_integration_secret(auth.access_token, str(payload.org_id), "jira")
    _, ciphertext = _ensure_connected_secret(row, "Jira")
    secret = decrypt_json(ciphertext)

    base_url = _as_clean_str(secret.get("base_url"), "base_url")
    email = _as_clean_str(secret.get("email"), "email")
    api_token = _as_clean_str(secret.get("api_token"), "api_token")
    project_key = _as_clean_str(secret.get("project_key"), "project_key")

    alert, finding = await _fetch_alert_and_finding(auth.access_token, str(payload.org_id), str(payload.alert_id))
    summary = f"[Verirule] {_as_clean_str(finding.get('title'), 'title')}"
    description = (
        f"Org ID: {_as_clean_str(alert.get('org_id'), 'org_id')}\n"
        f"Alert ID: {_as_clean_str(alert.get('id'), 'id')}\n"
        f"Severity: {_as_clean_str(finding.get('severity'), 'severity')}\n"
        f"Summary: {_as_clean_str(finding.get('summary'), 'summary')}\n"
        f"Alert link: /dashboard/alerts/{_as_clean_str(alert.get('id'), 'id')}?org_id={_as_clean_str(alert.get('org_id'), 'org_id')}"
    )

    issue = await create_issue(
        base_url=base_url,
        email=email,
        api_token=api_token,
        project_key=project_key,
        summary=summary,
        description=description,
    )
    return JiraCreateIssueOut.model_validate(issue)


@router.post("/integrations/{integration_type}/disable")
async def disable_integration(
    integration_type: str,
    payload: OrgIntegrationIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, bool]:
    if integration_type not in {"slack", "jira"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    await rpc_disable_integration(
        auth.access_token,
        {"p_org_id": str(payload.org_id), "p_type": integration_type},
    )
    return {"ok": True}
