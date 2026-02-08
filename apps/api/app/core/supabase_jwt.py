from collections.abc import Mapping

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.core.settings import get_settings


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


def verify_supabase_jwt(authorization: str | None = Header(default=None)) -> dict[str, object]:
    token = _extract_bearer_token(authorization)
    settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_ISSUER or not settings.SUPABASE_JWKS_URL:
        raise _unauthorized()

    try:
        signing_key = PyJWKClient(settings.SUPABASE_JWKS_URL).get_signing_key_from_jwt(token).key
        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            issuer=settings.SUPABASE_ISSUER,
        )
        if not isinstance(decoded, Mapping):
            raise _unauthorized()
        return dict(decoded)
    except HTTPException:
        raise
    except (InvalidTokenError, PyJWKClientError, ValueError):
        raise _unauthorized() from None
