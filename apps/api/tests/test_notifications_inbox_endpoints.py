from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints import notifications_inbox as inbox_endpoint
from app.auth.roles import OrgRoleContext
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.main import app

ORG_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "11111111-1111-1111-1111-111111111112"
OTHER_USER_ID = "11111111-1111-1111-1111-111111111113"
EVENT_ID = "11111111-1111-1111-1111-111111111114"
JOB_ID = "11111111-1111-1111-1111-111111111115"


def _auth(user_id: str = USER_ID) -> VerifiedSupabaseAuth:
    return VerifiedSupabaseAuth(access_token="token-123", claims={"sub": user_id})


def test_member_can_list_own_org_inbox(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    async def fake_enforce(auth, org_id: str, min_role: str) -> OrgRoleContext:
        assert auth.access_token == "token-123"
        assert org_id == ORG_ID
        assert min_role == "member"
        return OrgRoleContext(org_id=org_id, user_id=USER_ID, role="member")

    async def fake_list_events(access_token: str, **kwargs):
        assert access_token == "token-123"
        calls.append(kwargs)
        return [
            {
                "id": EVENT_ID,
                "org_id": ORG_ID,
                "user_id": USER_ID,
                "job_id": JOB_ID,
                "type": "immediate_alert",
                "entity_type": "alert",
                "entity_id": "11111111-1111-1111-1111-111111111116",
                "subject": "Immediate alert",
                "status": "sent",
                "attempts": 1,
                "last_error": None,
                "sent_at": "2026-02-14T00:05:00Z",
                "created_at": "2026-02-14T00:00:00Z",
                "read_at": None,
                "is_read": False,
            }
        ]

    monkeypatch.setattr(inbox_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(inbox_endpoint, "list_notification_events", fake_list_events)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/orgs/{ORG_ID}/notifications/inbox?limit=25")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()["events"]) == 1
    assert response.json()["events"][0]["id"] == EVENT_ID
    assert response.json()["events"][0]["is_read"] is False
    assert calls == [
        {
            "org_id": ORG_ID,
            "user_id": USER_ID,
            "limit": 25,
            "status_filter": None,
        }
    ]


def test_user_can_mark_own_event_read_and_unread(monkeypatch) -> None:
    reads: list[tuple[str, str, str]] = []
    unreads: list[tuple[str, str, str]] = []

    async def fake_get_event(access_token: str, event_id: str, **kwargs):
        assert access_token == "token-123"
        assert event_id == EVENT_ID
        return {
            "id": EVENT_ID,
            "org_id": ORG_ID,
            "user_id": USER_ID,
            "job_id": JOB_ID,
            "type": "immediate_alert",
            "subject": "Immediate alert",
            "status": "sent",
            "attempts": 1,
            "last_error": None,
            "sent_at": "2026-02-14T00:05:00Z",
            "created_at": "2026-02-14T00:00:00Z",
            "read_at": None,
            "is_read": False,
        }

    async def fake_mark_read(access_token: str, *, user_id: str, event_id: str) -> None:
        reads.append((access_token, user_id, event_id))

    async def fake_mark_unread(access_token: str, *, user_id: str, event_id: str) -> None:
        unreads.append((access_token, user_id, event_id))

    monkeypatch.setattr(inbox_endpoint, "get_notification_event", fake_get_event)
    monkeypatch.setattr(inbox_endpoint, "mark_notification_read", fake_mark_read)
    monkeypatch.setattr(inbox_endpoint, "mark_notification_unread", fake_mark_unread)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        read_response = client.post(f"/api/v1/notifications/{EVENT_ID}/read")
        unread_response = client.delete(f"/api/v1/notifications/{EVENT_ID}/read")
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 200
    assert unread_response.status_code == 200
    assert reads == [("token-123", USER_ID, EVENT_ID)]
    assert unreads == [("token-123", USER_ID, EVENT_ID)]


def test_user_cannot_mark_other_user_event_read_unread(monkeypatch) -> None:
    async def fake_get_event(access_token: str, event_id: str, **kwargs):
        assert access_token == "token-123"
        assert event_id == EVENT_ID
        return {
            "id": EVENT_ID,
            "org_id": ORG_ID,
            "user_id": OTHER_USER_ID,
            "job_id": JOB_ID,
            "type": "immediate_alert",
            "subject": "Immediate alert",
            "status": "sent",
            "attempts": 1,
            "last_error": None,
            "sent_at": "2026-02-14T00:05:00Z",
            "created_at": "2026-02-14T00:00:00Z",
        }

    async def fail_mark(*args, **kwargs):  # pragma: no cover
        raise AssertionError("mark helper should not run for foreign events")

    monkeypatch.setattr(inbox_endpoint, "get_notification_event", fake_get_event)
    monkeypatch.setattr(inbox_endpoint, "mark_notification_read", fail_mark)
    monkeypatch.setattr(inbox_endpoint, "mark_notification_unread", fail_mark)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        read_response = client.post(f"/api/v1/notifications/{EVENT_ID}/read")
        unread_response = client.delete(f"/api/v1/notifications/{EVENT_ID}/read")
    finally:
        app.dependency_overrides.clear()

    assert read_response.status_code == 403
    assert read_response.json() == {"detail": "Forbidden"}
    assert unread_response.status_code == 403
    assert unread_response.json() == {"detail": "Forbidden"}


def test_admin_can_requeue_notification_job(monkeypatch) -> None:
    requeue_calls: list[str] = []
    audits: list[dict[str, object]] = []

    async def fake_get_job(job_id: str):
        assert job_id == JOB_ID
        return {
            "id": JOB_ID,
            "org_id": ORG_ID,
            "type": "immediate_alert",
            "status": "failed",
            "attempts": 2,
            "last_error": "smtp failure",
        }

    async def fake_enforce(auth, org_id: str, min_role: str) -> OrgRoleContext:
        assert auth.access_token == "token-123"
        assert org_id == ORG_ID
        assert min_role == "admin"
        return OrgRoleContext(org_id=org_id, user_id=USER_ID, role="admin")

    async def fake_requeue(job_id: str) -> None:
        requeue_calls.append(job_id)

    async def fake_audit(access_token: str, payload: dict[str, object]) -> None:
        assert access_token == "token-123"
        audits.append(payload)

    monkeypatch.setattr(inbox_endpoint, "get_notification_job_service", fake_get_job)
    monkeypatch.setattr(inbox_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(inbox_endpoint, "requeue_notification_job", fake_requeue)
    monkeypatch.setattr(inbox_endpoint, "rpc_record_audit_event", fake_audit)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.post(f"/api/v1/notifications/jobs/{JOB_ID}/requeue")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"ok": True, "job_id": JOB_ID}
    assert requeue_calls == [JOB_ID]
    assert len(audits) == 1
    assert audits[0]["p_action"] == "notification_job_requeued"


def test_requeue_requires_admin(monkeypatch) -> None:
    async def fake_get_job(job_id: str):
        assert job_id == JOB_ID
        return {"id": JOB_ID, "org_id": ORG_ID, "status": "failed"}

    async def fake_enforce(*args, **kwargs):
        raise HTTPException(status_code=403, detail="Forbidden")

    async def fail_requeue(*args, **kwargs):  # pragma: no cover
        raise AssertionError("requeue should not run when admin guard fails")

    monkeypatch.setattr(inbox_endpoint, "get_notification_job_service", fake_get_job)
    monkeypatch.setattr(inbox_endpoint, "enforce_org_role", fake_enforce)
    monkeypatch.setattr(inbox_endpoint, "requeue_notification_job", fail_requeue)
    app.dependency_overrides[verify_supabase_auth] = _auth

    try:
        client = TestClient(app)
        response = client.post(f"/api/v1/notifications/jobs/{JOB_ID}/requeue")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}
