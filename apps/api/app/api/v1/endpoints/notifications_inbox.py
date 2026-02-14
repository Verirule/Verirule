from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.schemas.notifications_inbox import (
    NotificationDeliveryStatus,
    NotificationEventOut,
    NotificationInboxOut,
    NotificationReadStateOut,
    NotificationRequeueOut,
)
from app.auth.roles import OrgRoleContext, enforce_org_role
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    get_notification_event,
    get_notification_job_service,
    list_notification_events,
    mark_notification_read,
    mark_notification_unread,
    requeue_notification_job,
    rpc_record_audit_event,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)
limit_query = Query(default=50, ge=1, le=200)
status_filter_query = Query(default=None, alias="status")
user_id_query = Query(default=None)


def _claims_user_id(auth: VerifiedSupabaseAuth) -> str:
    sub = auth.claims.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return sub.strip()


@router.get("/orgs/{org_id}/notifications/inbox")
async def get_notifications_inbox(
    org_id: UUID,
    limit: int = limit_query,
    status_filter: NotificationDeliveryStatus | None = status_filter_query,
    user_id: UUID | None = user_id_query,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> NotificationInboxOut:
    org_id_value = str(org_id)
    role_ctx: OrgRoleContext = await enforce_org_role(auth, org_id_value, "member")

    effective_user_id = role_ctx.user_id
    if user_id is not None:
        requested_user_id = str(user_id)
        if requested_user_id != role_ctx.user_id:
            await enforce_org_role(auth, org_id_value, "admin")
        effective_user_id = requested_user_id

    rows = await list_notification_events(
        auth.access_token,
        org_id=org_id_value,
        user_id=effective_user_id,
        limit=limit,
        status_filter=status_filter,
    )
    return NotificationInboxOut(events=[NotificationEventOut.model_validate(row) for row in rows])


@router.post("/notifications/{event_id}/read")
async def mark_notifications_event_read(
    event_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> NotificationReadStateOut:
    actor_user_id = _claims_user_id(auth)
    row = await get_notification_event(
        auth.access_token,
        str(event_id),
        include_read_for_user_id=actor_user_id,
    )
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification event not found.")

    event_user_id = row.get("user_id")
    if not isinstance(event_user_id, str) or event_user_id.strip() != actor_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    await mark_notification_read(auth.access_token, user_id=actor_user_id, event_id=str(event_id))
    return NotificationReadStateOut(ok=True)


@router.delete("/notifications/{event_id}/read")
async def mark_notifications_event_unread(
    event_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> NotificationReadStateOut:
    actor_user_id = _claims_user_id(auth)
    row = await get_notification_event(
        auth.access_token,
        str(event_id),
        include_read_for_user_id=actor_user_id,
    )
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification event not found.")

    event_user_id = row.get("user_id")
    if not isinstance(event_user_id, str) or event_user_id.strip() != actor_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    await mark_notification_unread(auth.access_token, user_id=actor_user_id, event_id=str(event_id))
    return NotificationReadStateOut(ok=True)


@router.post("/notifications/jobs/{job_id}/requeue")
async def requeue_notifications_job(
    job_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> NotificationRequeueOut:
    row = await get_notification_job_service(str(job_id))
    if not isinstance(row, dict):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification job not found.")

    org_id = row.get("org_id")
    if not isinstance(org_id, str) or not org_id.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid notification job response from Supabase.",
        )

    role_ctx: OrgRoleContext = await enforce_org_role(auth, org_id.strip(), "admin")

    job_status = str(row.get("status") or "").strip().lower()
    if job_status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed notification jobs can be requeued.",
        )

    await requeue_notification_job(str(job_id))
    await rpc_record_audit_event(
        auth.access_token,
        {
            "p_org_id": org_id.strip(),
            "p_action": "notification_job_requeued",
            "p_entity_type": "notification_job",
            "p_entity_id": str(job_id),
            "p_metadata": {
                "actor_user_id": role_ctx.user_id,
            },
        },
    )
    return NotificationRequeueOut(ok=True, job_id=job_id)
