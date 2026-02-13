import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.schemas.tasks import (
    EvidenceFileDownloadUrlOut,
    EvidenceFileFinalizeIn,
    EvidenceFileOut,
    EvidenceFileUploadUrlIn,
    EvidenceFileUploadUrlOut,
)
from app.core.settings import get_settings
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    delete_evidence_file,
    insert_evidence_file,
    rpc_record_audit_event,
    select_evidence_file_by_id,
    select_evidence_files_by_task,
    select_task_by_id,
    update_evidence_file_finalize_service,
)
from app.core.supabase_storage_admin import (
    create_signed_download_url,
    create_signed_upload_url,
    delete_object,
)

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)

FILENAME_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]")
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".log"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "text/plain",
    "text/x-log",
}
ORG_ID_QUERY = Query(...)


def _auth_user_id_or_401(auth: VerifiedSupabaseAuth) -> str:
    subject = auth.claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return str(UUID(subject.strip()))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def _task_org_id_or_404(auth: VerifiedSupabaseAuth, task_id: UUID) -> str:
    task_row = await select_task_by_id(auth.access_token, str(task_id))
    if task_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    org_id = task_row.get("org_id")
    if not isinstance(org_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid task response from Supabase.",
        )
    return org_id


def _sanitize_filename(filename: str) -> str:
    trimmed = filename.strip()
    if not trimmed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")

    basename = trimmed.replace("\\", "/").split("/")[-1].strip()
    basename = FILENAME_SANITIZE_RE.sub("_", basename)
    basename = re.sub(r"_+", "_", basename)
    if not basename or basename in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename.")
    if len(basename) > 120:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename is too long.")

    extension = f".{basename.rsplit('.', 1)[-1].lower()}" if "." in basename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: pdf, png, jpg, txt, log.",
        )
    return basename


def _normalize_content_type(value: str | None) -> str | None:
    if value is None:
        return None
    content_type = value.strip().lower()
    if not content_type:
        return None
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported content type.",
        )
    return content_type


@router.post("/tasks/{task_id}/evidence-files/upload-url")
async def create_evidence_upload_url(
    task_id: UUID,
    payload: EvidenceFileUploadUrlIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> EvidenceFileUploadUrlOut:
    settings = get_settings()
    task_org_id = await _task_org_id_or_404(auth, task_id)
    if str(payload.org_id) != task_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task is not in this org.")
    if payload.byte_size > settings.MAX_EVIDENCE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Evidence file exceeds maximum upload size.",
        )

    safe_filename = _sanitize_filename(payload.filename)
    content_type = _normalize_content_type(payload.content_type)
    object_path = f"orgs/{task_org_id}/tasks/{task_id}/{uuid4()}_{safe_filename}"
    bucket = settings.EVIDENCE_BUCKET_NAME

    created = await insert_evidence_file(
        auth.access_token,
        {
            "org_id": task_org_id,
            "task_id": str(task_id),
            "filename": safe_filename,
            "storage_bucket": bucket,
            "storage_path": object_path,
            "content_type": content_type,
            "byte_size": payload.byte_size,
        },
    )
    evidence_file_id = created.get("id")
    if not isinstance(evidence_file_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid evidence file create response from Supabase.",
        )

    signed = await create_signed_upload_url(
        bucket=bucket,
        path=object_path,
        content_type=content_type,
        expires=settings.EVIDENCE_SIGNED_URL_SECONDS,
    )
    return EvidenceFileUploadUrlOut(
        evidence_file_id=UUID(evidence_file_id),
        bucket=bucket,
        path=signed["path"],
        signed_upload_url=signed["signed_url"],
        expires_in=settings.EVIDENCE_SIGNED_URL_SECONDS,
    )


@router.post("/evidence-files/{evidence_file_id}/finalize")
async def finalize_evidence_upload(
    evidence_file_id: UUID,
    payload: EvidenceFileFinalizeIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, bool]:
    user_id = _auth_user_id_or_401(auth)
    evidence = await select_evidence_file_by_id(auth.access_token, str(evidence_file_id), str(payload.org_id))
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    updated = await update_evidence_file_finalize_service(
        evidence_file_id=str(evidence_file_id),
        org_id=str(payload.org_id),
        sha256=payload.sha256.lower(),
        uploaded_by=user_id,
    )

    await rpc_record_audit_event(
        auth.access_token,
        {
            "p_org_id": str(payload.org_id),
            "p_action": "evidence_uploaded",
            "p_entity_type": "evidence_file",
            "p_entity_id": str(evidence_file_id),
            "p_metadata": {
                "task_id": updated.get("task_id"),
                "filename": updated.get("filename"),
                "storage_path": updated.get("storage_path"),
                "byte_size": updated.get("byte_size"),
                "sha256": payload.sha256.lower(),
            },
        },
    )

    return {"ok": True}


@router.get("/tasks/{task_id}/evidence-files")
async def list_task_evidence_files(
    task_id: UUID,
    org_id: UUID = ORG_ID_QUERY,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[EvidenceFileOut]]:
    task_org_id = await _task_org_id_or_404(auth, task_id)
    if str(org_id) != task_org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task is not in this org.")

    rows = await select_evidence_files_by_task(auth.access_token, str(task_id), str(org_id))
    return {"evidence_files": [EvidenceFileOut.model_validate(row) for row in rows]}


@router.get("/evidence-files/{evidence_file_id}/download-url")
async def get_evidence_download_url(
    evidence_file_id: UUID,
    org_id: UUID = ORG_ID_QUERY,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> EvidenceFileDownloadUrlOut:
    settings = get_settings()
    evidence = await select_evidence_file_by_id(auth.access_token, str(evidence_file_id), str(org_id))
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    bucket = evidence.get("storage_bucket")
    storage_path = evidence.get("storage_path")
    if not isinstance(bucket, str) or not isinstance(storage_path, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid evidence file response from Supabase.",
        )

    signed = await create_signed_download_url(
        bucket=bucket,
        path=storage_path,
        expires=settings.EVIDENCE_SIGNED_URL_SECONDS,
    )
    return EvidenceFileDownloadUrlOut(
        download_url=signed["signed_url"],
        expires_in=settings.EVIDENCE_SIGNED_URL_SECONDS,
    )


@router.delete("/evidence-files/{evidence_file_id}")
async def delete_evidence_file_endpoint(
    evidence_file_id: UUID,
    org_id: UUID = ORG_ID_QUERY,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, bool]:
    evidence = await select_evidence_file_by_id(auth.access_token, str(evidence_file_id), str(org_id))
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    bucket = evidence.get("storage_bucket")
    storage_path = evidence.get("storage_path")
    if not isinstance(bucket, str) or not isinstance(storage_path, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid evidence file response from Supabase.",
        )

    await delete_object(bucket, storage_path)
    await delete_evidence_file(auth.access_token, str(evidence_file_id), str(org_id))

    await rpc_record_audit_event(
        auth.access_token,
        {
            "p_org_id": str(org_id),
            "p_action": "evidence_deleted",
            "p_entity_type": "evidence_file",
            "p_entity_id": str(evidence_file_id),
            "p_metadata": {
                "task_id": evidence.get("task_id"),
                "filename": evidence.get("filename"),
                "storage_path": storage_path,
                "byte_size": evidence.get("byte_size"),
            },
        },
    )
    return {"ok": True}
