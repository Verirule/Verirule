from dataclasses import dataclass
from typing import Any

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.core.settings import get_settings


@dataclass(frozen=True)
class VerifiedSupabaseAuth:
    access_token: str
    claims: dict[str, Any]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _unauthorized()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized()

    return token.strip()


def _decode_supabase_token(token: str) -> dict[str, Any]:
    settings = get_settings()

    try:
        signing_key = PyJWKClient(settings.SUPABASE_JWKS_URL).get_signing_key_from_jwt(token).key
        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            issuer=settings.SUPABASE_ISSUER,
            options={"verify_aud": False},
        )
        if not isinstance(decoded, dict):
            raise _unauthorized()
        return decoded
    except HTTPException:
        raise
    except (InvalidTokenError, PyJWKClientError, ValueError):
        raise _unauthorized() from None


def verify_bearer_token(auth_header: str) -> dict[str, Any]:
    token = _extract_bearer_token(auth_header)
    return _decode_supabase_token(token)


def verify_supabase_jwt(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    return verify_bearer_token(authorization or "")


def verify_supabase_auth(authorization: str | None = Header(default=None)) -> VerifiedSupabaseAuth:
    token = _extract_bearer_token(authorization)
    return VerifiedSupabaseAuth(access_token=token, claims=_decode_supabase_token(token))
