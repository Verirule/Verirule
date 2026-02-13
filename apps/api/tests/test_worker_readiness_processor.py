import asyncio

from app.worker import readiness_processor


def test_readiness_processor_computes_for_active_orgs(monkeypatch) -> None:
    computed_orgs: list[str] = []

    async def fake_active_orgs(limit_per_table: int = 2000) -> list[str]:
        assert limit_per_table == 2000
        return [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
        ]

    async def fake_compute(access_token: str, org_id: str) -> str:
        assert access_token == "service-role-token"
        computed_orgs.append(org_id)
        return "snapshot-id"

    monkeypatch.setattr(readiness_processor, "list_active_org_ids_service", fake_active_orgs)
    monkeypatch.setattr(readiness_processor, "rpc_compute_org_readiness", fake_compute)

    processor = readiness_processor.ReadinessProcessor(
        access_token="service-role-token",
        interval_seconds=900,
    )
    result = asyncio.run(processor.process_if_due())

    assert result == 2
    assert computed_orgs == [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ]


def test_readiness_processor_respects_interval(monkeypatch) -> None:
    compute_calls = 0

    async def fake_active_orgs(limit_per_table: int = 2000) -> list[str]:
        return ["11111111-1111-1111-1111-111111111111"]

    async def fake_compute(access_token: str, org_id: str) -> str:
        nonlocal compute_calls
        compute_calls += 1
        return "snapshot-id"

    monkeypatch.setattr(readiness_processor, "list_active_org_ids_service", fake_active_orgs)
    monkeypatch.setattr(readiness_processor, "rpc_compute_org_readiness", fake_compute)

    processor = readiness_processor.ReadinessProcessor(
        access_token="service-role-token",
        interval_seconds=900,
    )

    first = asyncio.run(processor.process_if_due())
    second = asyncio.run(processor.process_if_due())

    assert first == 1
    assert second == 0
    assert compute_calls == 1
