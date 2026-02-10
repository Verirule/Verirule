import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas.tasks import (
    TaskEvidenceDownloadUrlOut,
    TaskEvidenceFileIn,
    TaskEvidenceUploadUrlIn,
    TaskEvidenceUploadUrlOut,
)
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import (
    rpc_add_task_evidence,
    select_task_by_id,
    select_task_evidence_by_id,
)
from app.core.supabase_storage import create_signed_download_url, create_signed_upload_url

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)

EVIDENCE_BUCKET = "evidence"
SIGNED_URL_EXPIRY_SECONDS = 300
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
ALLOWED_CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg", "text/plain"}
FILENAME_SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]")


async def _get_task_or_404(auth: VerifiedSupabaseAuth, task_id: UUID) -> tuple[str, str]:
    task_row = await select_task_by_id(auth.access_token, str(task_id))
    if task_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    row_task_id = task_row.get("id")
    org_id = task_row.get("org_id")
    if not isinstance(row_task_id, str) or not isinstance(org_id, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid task response from Supabase.",
        )

    return row_task_id, org_id


def _sanitize_filename(value: str) -> str:
    trimmed = value.strip()
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
            detail="Unsupported file type. Allowed: pdf, png, jpg, txt.",
        )

    return basename


def _validate_content_type(value: str | None) -> None:
    if value is None:
        return
    content_type = value.strip().lower()
    if not content_type:
        return
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported content type.",
        )


@router.post("/tasks/{task_id}/evidence/upload-url")
async def create_task_evidence_upload_url(
    task_id: UUID,
    payload: TaskEvidenceUploadUrlIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> TaskEvidenceUploadUrlOut:
    _, org_id = await _get_task_or_404(auth, task_id)
    safe_filename = _sanitize_filename(payload.filename)
    _validate_content_type(payload.content_type)

    object_path = f"org/{org_id}/tasks/{task_id}/{uuid4()}-{safe_filename}"
    signed = await create_signed_upload_url(EVIDENCE_BUCKET, object_path, SIGNED_URL_EXPIRY_SECONDS)

    return TaskEvidenceUploadUrlOut(
        path=signed["path"],
        uploadUrl=signed["signed_url"],
        expiresIn=SIGNED_URL_EXPIRY_SECONDS,
    )


@router.post("/tasks/{task_id}/evidence/file")
async def create_task_file_evidence(
    task_id: UUID,
    payload: TaskEvidenceFileIn,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, UUID]:
    _, org_id = await _get_task_or_404(auth, task_id)

    ref_path = payload.path.strip()
    expected_prefix = f"org/{org_id}/tasks/{task_id}/"
    if not ref_path.startswith(expected_prefix):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid evidence path.")

    evidence_id = await rpc_add_task_evidence(
        auth.access_token,
        {"p_task_id": str(task_id), "p_type": "file", "p_ref": ref_path},
    )
    return {"id": UUID(evidence_id)}


@router.get("/tasks/{task_id}/evidence/{evidence_id}/download-url")
async def get_task_evidence_download_url(
    task_id: UUID,
    evidence_id: UUID,
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> TaskEvidenceDownloadUrlOut:
    _, org_id = await _get_task_or_404(auth, task_id)
    evidence = await select_task_evidence_by_id(auth.access_token, str(task_id), str(evidence_id))
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    evidence_type = evidence.get("type")
    evidence_ref = evidence.get("ref")
    if evidence_type != "file" or not isinstance(evidence_ref, str):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence file not found.")

    expected_prefix = f"org/{org_id}/tasks/{task_id}/"
    if not evidence_ref.startswith(expected_prefix):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid evidence path.")

    signed = await create_signed_download_url(EVIDENCE_BUCKET, evidence_ref, SIGNED_URL_EXPIRY_SECONDS)
    return TaskEvidenceDownloadUrlOut(
        downloadUrl=signed["signed_url"],
        expiresIn=SIGNED_URL_EXPIRY_SECONDS,
    )
