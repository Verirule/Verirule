from app.billing.entitlements import Plan, get_entitlements, parse_plan


def test_parse_plan_defaults_to_free() -> None:
    assert parse_plan(None) is Plan.FREE
    assert parse_plan("invalid") is Plan.FREE


def test_free_plan_entitlements() -> None:
    entitlements = get_entitlements(Plan.FREE)
    assert entitlements.plan is Plan.FREE
    assert entitlements.integrations_enabled is False
    assert entitlements.exports_enabled is True
    assert entitlements.scheduling_enabled is True
    assert entitlements.max_sources == 3
    assert entitlements.max_exports_per_month == 1
    assert entitlements.max_members == 5


def test_pro_plan_entitlements() -> None:
    entitlements = get_entitlements(Plan.PRO)
    assert entitlements.plan is Plan.PRO
    assert entitlements.integrations_enabled is True
    assert entitlements.exports_enabled is True
    assert entitlements.scheduling_enabled is True
    assert entitlements.max_sources == 25
    assert entitlements.max_integrations == 10
    assert entitlements.max_members == 25


def test_business_plan_entitlements() -> None:
    entitlements = get_entitlements(Plan.BUSINESS)
    assert entitlements.plan is Plan.BUSINESS
    assert entitlements.integrations_enabled is True
    assert entitlements.exports_enabled is True
    assert entitlements.scheduling_enabled is True
    assert entitlements.max_sources == 100
    assert entitlements.max_exports_per_month == 500
    assert entitlements.max_members == 100
