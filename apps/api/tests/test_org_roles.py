import asyncio

import pytest
from fastapi import HTTPException

from app.auth import roles
from app.core.supabase_jwt import VerifiedSupabaseAuth

ORG_ID = "11111111-1111-1111-1111-111111111111"


def test_enforce_org_role_denies_viewer(monkeypatch) -> None:
    async def fake_select_org_member_role(access_token: str, org_id: str, user_id: str) -> str | None:
        assert access_token == "token-123"
        assert org_id == ORG_ID
        assert user_id == "11111111-1111-1111-1111-111111111112"
        return "viewer"

    monkeypatch.setattr(roles, "select_org_member_role", fake_select_org_member_role)

    auth = VerifiedSupabaseAuth(
        access_token="token-123",
        claims={"sub": "11111111-1111-1111-1111-111111111112"},
    )

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(roles.enforce_org_role(auth, ORG_ID, "admin"))

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Forbidden"
