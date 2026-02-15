import asyncio

from app.worker import alert_task_processor

ORG_ID = "11111111-1111-1111-1111-111111111111"
ALERT_ID = "22222222-2222-2222-2222-222222222222"
FINDING_ID = "33333333-3333-3333-3333-333333333333"
TASK_ID = "44444444-4444-4444-4444-444444444444"


def test_processor_creates_task_links_controls_and_evidence(monkeypatch) -> None:
    linked: list[tuple[str, str, str]] = []
    evidence_batch_sizes: list[int] = []

    async def fake_select_alerts(limit: int = 50):
        assert limit == 25
        return [
            {
                "id": ALERT_ID,
                "org_id": ORG_ID,
                "finding_id": FINDING_ID,
                "task_id": None,
                "status": "open",
                "created_at": "2026-02-13T00:00:00Z",
            }
        ]

    async def fake_ensure(access_token: str, org_id: str) -> None:
        assert access_token == "service-role-token"
        assert org_id == ORG_ID

    async def fake_get_rules(access_token: str, org_id: str):
        return {
            "enabled": True,
            "auto_create_task_on_alert": True,
            "min_severity": "medium",
            "auto_link_suggested_controls": True,
            "auto_add_evidence_checklist": True,
        }

    async def fake_select_finding(access_token: str, finding_id: str):
        assert finding_id == FINDING_ID
        return {
            "id": FINDING_ID,
            "org_id": ORG_ID,
            "title": "Access rule changed",
            "summary": "Firewall ingress rule was broadened.",
            "severity": "high",
            "raw_url": "https://example.com/firewall",
        }

    async def fake_insert_task(
        org_id: str,
        *,
        title: str,
        description: str | None,
        alert_id: str | None,
        finding_id: str | None,
        due_at: str | None = None,
        severity: str | None = None,
        sla_state: str = "none",
    ) -> str:
        assert org_id == ORG_ID
        assert alert_id == ALERT_ID
        assert finding_id == FINDING_ID
        assert "remediation" in title.lower()
        assert isinstance(description, str)
        assert due_at == "2026-02-14T00:00:00Z"
        assert severity == "high"
        assert sla_state == "on_track"
        return TASK_ID

    async def fake_compute_due_at(
        access_token: str,
        *,
        org_id: str,
        severity: str,
        created_at: str | None,
    ) -> str:
        assert access_token == "service-role-token"
        assert org_id == ORG_ID
        assert severity == "high"
        assert created_at == "2026-02-13T00:00:00Z"
        return "2026-02-14T00:00:00Z"

    async def fake_link(access_token: str, org_id: str, alert_id: str, task_id: str) -> None:
        linked.append((org_id, alert_id, task_id))

    async def fake_resolve_controls(*args, **kwargs):
        return ["55555555-5555-5555-5555-555555555555"]

    async def fake_insert_task_controls(org_id: str, task_id: str, control_ids: list[str]) -> int:
        assert org_id == ORG_ID
        assert task_id == TASK_ID
        assert control_ids == ["55555555-5555-5555-5555-555555555555"]
        return 1

    async def fake_list_control_evidence(access_token: str, control_ids: list[str]):
        assert control_ids == ["55555555-5555-5555-5555-555555555555"]
        return [
            {
                "control_id": control_ids[0],
                "label": "Firewall change ticket",
                "description": "Attach approved change request",
                "evidence_type": "ticket",
                "required": True,
            }
        ]

    async def fake_insert_task_evidence(org_id: str, task_id: str, evidence_items: list[dict[str, str]]) -> int:
        assert org_id == ORG_ID
        assert task_id == TASK_ID
        evidence_batch_sizes.append(len(evidence_items))
        return len(evidence_items)

    monkeypatch.setattr(alert_task_processor, "select_alerts_needing_tasks_service", fake_select_alerts)
    monkeypatch.setattr(alert_task_processor, "ensure_alert_task_rules", fake_ensure)
    monkeypatch.setattr(alert_task_processor, "get_alert_task_rules", fake_get_rules)
    monkeypatch.setattr(alert_task_processor, "select_finding_by_id", fake_select_finding)
    monkeypatch.setattr(alert_task_processor, "rpc_compute_task_due_at", fake_compute_due_at)
    monkeypatch.setattr(alert_task_processor, "insert_task_service", fake_insert_task)
    monkeypatch.setattr(alert_task_processor, "update_alert_task_id", fake_link)
    monkeypatch.setattr(alert_task_processor, "resolve_control_ids_for_alert", fake_resolve_controls)
    monkeypatch.setattr(alert_task_processor, "bulk_insert_task_controls_service", fake_insert_task_controls)
    monkeypatch.setattr(alert_task_processor, "list_control_evidence_items", fake_list_control_evidence)
    monkeypatch.setattr(alert_task_processor, "bulk_insert_task_evidence_service", fake_insert_task_evidence)

    processor = alert_task_processor.AlertTaskProcessor(access_token="service-role-token")
    processed = asyncio.run(processor.process_alerts_once(limit=25))

    assert processed == 1
    assert linked == [(ORG_ID, ALERT_ID, TASK_ID)]
    assert evidence_batch_sizes == [1]


def test_processor_skips_when_min_severity_not_met(monkeypatch) -> None:
    created_tasks = 0

    async def fake_select_alerts(limit: int = 50):
        return [
            {
                "id": ALERT_ID,
                "org_id": ORG_ID,
                "finding_id": FINDING_ID,
                "task_id": None,
                "status": "open",
            }
        ]

    async def fake_ensure(access_token: str, org_id: str) -> None:
        return None

    async def fake_get_rules(access_token: str, org_id: str):
        return {
            "enabled": True,
            "auto_create_task_on_alert": True,
            "min_severity": "high",
            "auto_link_suggested_controls": True,
            "auto_add_evidence_checklist": True,
        }

    async def fake_select_finding(access_token: str, finding_id: str):
        return {
            "id": FINDING_ID,
            "org_id": ORG_ID,
            "title": "Minor text change",
            "summary": "A low-impact wording update.",
            "severity": "low",
        }

    async def fake_insert_task(*args, **kwargs) -> str:
        nonlocal created_tasks
        created_tasks += 1
        return TASK_ID

    async def fake_compute_due_at(*args, **kwargs) -> str:
        return "2026-02-14T00:00:00Z"

    monkeypatch.setattr(alert_task_processor, "select_alerts_needing_tasks_service", fake_select_alerts)
    monkeypatch.setattr(alert_task_processor, "ensure_alert_task_rules", fake_ensure)
    monkeypatch.setattr(alert_task_processor, "get_alert_task_rules", fake_get_rules)
    monkeypatch.setattr(alert_task_processor, "select_finding_by_id", fake_select_finding)
    monkeypatch.setattr(alert_task_processor, "rpc_compute_task_due_at", fake_compute_due_at)
    monkeypatch.setattr(alert_task_processor, "insert_task_service", fake_insert_task)

    processor = alert_task_processor.AlertTaskProcessor(access_token="service-role-token")
    processed = asyncio.run(processor.process_alerts_once(limit=25))

    assert processed == 0
    assert created_tasks == 0


def test_processor_is_idempotent_when_alert_already_has_task(monkeypatch) -> None:
    created_tasks = 0

    async def fake_select_alerts(limit: int = 50):
        return [
            {
                "id": ALERT_ID,
                "org_id": ORG_ID,
                "finding_id": FINDING_ID,
                "task_id": TASK_ID,
                "status": "open",
            }
        ]

    async def fake_insert_task(*args, **kwargs) -> str:
        nonlocal created_tasks
        created_tasks += 1
        return TASK_ID

    monkeypatch.setattr(alert_task_processor, "select_alerts_needing_tasks_service", fake_select_alerts)
    monkeypatch.setattr(alert_task_processor, "insert_task_service", fake_insert_task)

    processor = alert_task_processor.AlertTaskProcessor(access_token="service-role-token")
    processed = asyncio.run(processor.process_alerts_once(limit=25))

    assert processed == 0
    assert created_tasks == 0
