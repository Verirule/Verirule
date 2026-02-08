from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from supabase import Client

from ..config import Settings
from ..supabase_client import get_supabase_service_client


FREE_INGESTION_COOLDOWN_HOURS = 24
FREE_MAX_BUSINESSES = 1
FREE_ALERTS_MAX = 25


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def get_subscription(client: Client, user_id: str) -> Optional[Dict]:
    result = (
        client.table("subscriptions")
        .select("id, user_id, plan, status, started_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_subscription_plan(client: Client, user_id: str) -> str:
    subscription = get_subscription(client, user_id)
    if not subscription:
        return "free"
    if subscription.get("status") != "active":
        return "free"
    return subscription.get("plan") or "free"


def enforce_business_limit(client: Client, user_id: str) -> None:
    plan = get_subscription_plan(client, user_id)
    if plan != "free":
        return

    result = (
        client.table("business_profiles")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )
    count = len(result.data or [])
    if count >= FREE_MAX_BUSINESSES:
        raise RuntimeError("Free plan limit reached: maximum 1 business")


def enforce_ingestion_limit(client: Client, user_id: str) -> None:
    plan = get_subscription_plan(client, user_id)
    if plan != "free":
        return

    result = (
        client.table("regulation_versions")
        .select("detected_at")
        .order("detected_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return

    detected_at = result.data[0].get("detected_at")
    if not detected_at:
        return

    try:
        last = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
    except ValueError:
        return

    if _utc_now() - last < timedelta(hours=FREE_INGESTION_COOLDOWN_HOURS):
        raise RuntimeError("Free plan ingestion cooldown active")


def alert_limit_for_user(client: Client, user_id: str) -> int:
    plan = get_subscription_plan(client, user_id)
    if plan == "free":
        return FREE_ALERTS_MAX
    return 1000


def get_service_client(settings: Settings) -> Client:
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")
    return get_supabase_service_client(settings)
