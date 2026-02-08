from typing import Dict

import jwt
from fastapi import Depends, HTTPException, Request, status

from .config import Settings, get_settings


def _extract_role(payload: Dict) -> str | None:
    if isinstance(payload.get("role"), str):
        return payload["role"]
    app_meta = payload.get("app_metadata") or {}
    if isinstance(app_meta.get("role"), str):
        return app_meta["role"]
    user_meta = payload.get("user_metadata") or {}
    if isinstance(user_meta.get("role"), str):
        return user_meta["role"]
    return None


def validate_jwt(request: Request, settings: Settings = Depends(get_settings)) -> Dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    token = auth_header.replace("Bearer ", "", 1).strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    try:
        payload = jwt.decode(
            token, settings.SUPABASE_JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return {
        "user_id": payload.get("sub") or payload.get("user_id"),
        "role": _extract_role(payload),
        "claims": payload,
    }
