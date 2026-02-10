from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.schemas.tasks import (
    TaskCommentIn,
    TaskCommentOut,
    TaskCreateIn,
    TaskEvidenceIn,
    TaskEvidenceOut,
    TaskOut,
    TaskStatusIn,
)
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    rpc_add_task_comment,
    rpc_add_task_evidence,
    rpc_create_task,
    rpc_set_task_status,
    select_task_comments,
    select_task_evidence,
    select_tasks,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/tasks")
async def tasks(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[TaskOut]]:
    rows = await select_tasks(auth.access_token, str(org_id))
    return {"tasks": [TaskOut.model_validate(row) for row in rows]}


@router.post("/tasks")
async def create_task(
    payload: TaskCreateIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, UUID]:
    task_id = await rpc_create_task(
        auth.access_token,
        {
            "p_org_id": str(payload.org_id),
            "p_title": payload.title,
            "p_description": payload.description,
            "p_alert_id": str(payload.alert_id) if payload.alert_id else None,
            "p_finding_id": str(payload.finding_id) if payload.finding_id else None,
            "p_due_at": payload.due_at.isoformat() if payload.due_at else None,
        },
    )
    return {"id": UUID(task_id)}


@router.get("/tasks/{task_id}/comments")
async def task_comments(
    task_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[TaskCommentOut]]:
    rows = await select_task_comments(auth.access_token, str(task_id))
    return {"comments": [TaskCommentOut.model_validate(row) for row in rows]}


@router.post("/tasks/{task_id}/comments")
async def create_task_comment(
    task_id: UUID, payload: TaskCommentIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, UUID]:
    comment_id = await rpc_add_task_comment(
        auth.access_token,
        {"p_task_id": str(task_id), "p_body": payload.body},
    )
    return {"id": UUID(comment_id)}


@router.get("/tasks/{task_id}/evidence")
async def task_evidence(
    task_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, list[TaskEvidenceOut]]:
    rows = await select_task_evidence(auth.access_token, str(task_id))
    return {"evidence": [TaskEvidenceOut.model_validate(row) for row in rows]}


@router.post("/tasks/{task_id}/evidence")
async def create_task_evidence(
    task_id: UUID, payload: TaskEvidenceIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, UUID]:
    evidence_id = await rpc_add_task_evidence(
        auth.access_token,
        {"p_task_id": str(task_id), "p_type": payload.type, "p_ref": payload.ref},
    )
    return {"id": UUID(evidence_id)}


@router.patch("/tasks/{task_id}/status")
async def update_task_status(
    task_id: UUID, payload: TaskStatusIn, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> dict[str, bool]:
    await rpc_set_task_status(
        auth.access_token,
        {"p_task_id": str(task_id), "p_status": payload.status},
    )
    return {"ok": True}
