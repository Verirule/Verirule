import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status

from app.core.settings import get_settings


def _get_fernet() -> Fernet:
    secrets_key = get_settings().VERIRULE_SECRETS_KEY
    if not secrets_key or not secrets_key.strip():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Integration secrets are not configured.",
        )

    digest = hashlib.sha256(secrets_key.encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_json(obj: dict[str, Any]) -> str:
    serialized = json.dumps(obj, separators=(",", ":"), ensure_ascii=True)
    return _get_fernet().encrypt(serialized.encode("utf-8")).decode("utf-8")


def decrypt_json(ciphertext: str) -> dict[str, Any]:
    try:
        plaintext = _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored integration secret cannot be decrypted.",
        ) from exc

    try:
        payload = json.loads(plaintext)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored integration secret is invalid.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored integration secret is invalid.",
        )

    return payload
