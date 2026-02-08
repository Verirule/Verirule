from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from supabase import Client

from ..alerts.service import generate_alert_for_violation
from ..config import Settings
from ..supabase_client import get_supabase_service_client

logger = logging.getLogger(__name__)


Condition = Dict[str, Any]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _evaluate_simple(condition: Condition, context: Dict[str, Any]) -> bool | None:
    field = condition.get("field")
    op = condition.get("op")
    value = condition.get("value")
    if not field or op is None:
        return None

    actual = context.get(field)
    try:
        if op == "==":
            return actual == value
        if op == "!=":
            return actual != value
        if op == ">":
            return actual > value
        if op == ">=":
            return actual >= value
        if op == "<":
            return actual < value
        if op == "<=":
            return actual <= value
        if op == "in":
            return actual in value
        if op == "contains":
            return value in actual
    except Exception:
        return None
    return None


def evaluate_condition(condition: Condition, context: Dict[str, Any]) -> bool | None:
    """Evaluate a condition against a context dict.

    Supported shapes:
    - {"field": "field_name", "op": "==", "value": 123}
    - {"and": [cond, cond]}
    - {"or": [cond, cond]}
    """
    if "and" in condition:
        results = [evaluate_condition(c, context) for c in condition.get("and", [])]
        if any(r is None for r in results):
            return None
        return all(results)
    if "or" in condition:
        results = [evaluate_condition(c, context) for c in condition.get("or", [])]
        if all(r is None for r in results):
            return None
        return any(r is True for r in results)
    return _evaluate_simple(condition, context)


def _get_business_profile(client: Client, business_id: str) -> Dict[str, Any]:
    result = (
        client.table("business_profiles")
        .select("*")
        .eq("id", business_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise RuntimeError("Business profile not found")
    return result.data[0]


def _get_applicable_regulations(
    client: Client, industry: str | None, jurisdiction: str | None
) -> Iterable[Dict[str, Any]]:
    query = client.table("regulations").select("id, title, industry, jurisdiction")
    if industry:
        query = query.eq("industry", industry)
    if jurisdiction:
        query = query.eq("jurisdiction", jurisdiction)
    return query.execute().data


def _get_rules(client: Client, regulation_ids: list[str]) -> Iterable[Dict[str, Any]]:
    if not regulation_ids:
        return []
    return (
        client.table("compliance_rules")
        .select("id, regulation_id, rule_description, severity, condition")
        .in_("regulation_id", regulation_ids)
        .execute()
        .data
    )


def _upsert_status(
    client: Client, business_id: str, regulation_id: str, status: str
) -> None:
    existing = (
        client.table("business_compliance_status")
        .select("id")
        .eq("business_id", business_id)
        .eq("regulation_id", regulation_id)
        .limit(1)
        .execute()
    )
    payload = {
        "business_id": business_id,
        "regulation_id": regulation_id,
        "status": status,
        "last_checked_at": _utc_now(),
    }
    if existing.data:
        client.table("business_compliance_status").update(payload).eq(
            "id", existing.data[0]["id"]
        ).execute()
    else:
        client.table("business_compliance_status").insert(payload).execute()


def _insert_violation(
    client: Client,
    business_id: str,
    regulation_id: str,
    rule_id: str,
    severity: str,
    message: str,
) -> Dict[str, Any] | None:
    existing = (
        client.table("violations")
        .select("id")
        .eq("business_id", business_id)
        .eq("regulation_id", regulation_id)
        .eq("rule_id", rule_id)
        .eq("resolved", False)
        .limit(1)
        .execute()
    )
    if existing.data:
        return None
    result = client.table("violations").insert(
        {
            "business_id": business_id,
            "regulation_id": regulation_id,
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
        }
    ).execute()
    return result.data[0] if result.data else None


def evaluate_business_compliance(
    settings: Settings,
    business_id: str,
    client: Client | None = None,
) -> Dict[str, int]:
    """Evaluate compliance for a single business profile.

    Returns counts for evaluated rules and violations created.
    """
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for compliance evaluation")

    if client is None:
        client = get_supabase_service_client(settings)

    profile = _get_business_profile(client, business_id)
    regulations = list(
        _get_applicable_regulations(
            client, profile.get("industry"), profile.get("jurisdiction")
        )
    )
    regulation_ids = [r["id"] for r in regulations]
    regulation_titles = {r["id"]: r.get("title", "Regulation") for r in regulations}
    rules = list(_get_rules(client, regulation_ids))

    evaluated = 0
    violations = 0

    for rule in rules:
        evaluated += 1
        condition = rule.get("condition") or {}
        result = evaluate_condition(condition, profile)

        if result is True:
            _upsert_status(client, profile["id"], rule["regulation_id"], "compliant")
            continue
        if result is False:
            _upsert_status(client, profile["id"], rule["regulation_id"], "non_compliant")
            violation = _insert_violation(
                client,
                profile["id"],
                rule["regulation_id"],
                rule["id"],
                rule.get("severity", "medium"),
                rule.get("rule_description", "Rule violation"),
            )
            if violation:
                generate_alert_for_violation(
                    settings,
                    violation,
                    profile.get("business_name", "Business"),
                    regulation_titles.get(rule["regulation_id"], "Regulation"),
                    profile.get("user_id"),
                    client=client,
                )
                violations += 1
            continue

        _upsert_status(client, profile["id"], rule["regulation_id"], "unknown")

    logger.info(
        "Compliance evaluation finished for business_id=%s, evaluated=%s, violations=%s",
        business_id,
        evaluated,
        violations,
    )

    return {"evaluated": evaluated, "violations": violations}
