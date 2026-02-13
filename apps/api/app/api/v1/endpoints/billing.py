from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.schemas.billing import BillingEventOut, BillingOut
from app.billing.entitlements import get_entitlements, parse_plan
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import select_billing_events, select_org_billing

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/orgs/{org_id}/billing")
async def billing(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> BillingOut:
    row = await select_org_billing(auth.access_token, str(org_id))
    raw_plan = row.get("plan") if isinstance(row, dict) else None
    plan = parse_plan(raw_plan if isinstance(raw_plan, str) else None)
    entitlements = get_entitlements(plan).as_dict()
    entitlements["plan"] = plan.value

    return BillingOut.model_validate(
        {
            "org_id": row.get("id") if isinstance(row, dict) else str(org_id),
            "plan": plan.value,
            "plan_status": (
                row.get("plan_status")
                if isinstance(row, dict) and row.get("plan_status") in {"active", "past_due", "canceled", "trialing"}
                else "active"
            ),
            "stripe_customer_id": row.get("stripe_customer_id") if isinstance(row, dict) else None,
            "stripe_subscription_id": row.get("stripe_subscription_id") if isinstance(row, dict) else None,
            "current_period_end": row.get("current_period_end") if isinstance(row, dict) else None,
            "entitlements": entitlements,
        }
    )


@router.get("/orgs/{org_id}/billing/events")
async def billing_events(
    org_id: UUID,
    limit: int = Query(default=25, ge=1, le=100),
    auth: VerifiedSupabaseAuth = supabase_auth_dependency,
) -> dict[str, list[BillingEventOut]]:
    rows = await select_billing_events(auth.access_token, str(org_id), limit=limit)
    events = [
        BillingEventOut.model_validate(
            {
                "id": row.get("id"),
                "org_id": row.get("org_id") or str(org_id),
                "stripe_event_id": row.get("stripe_event_id"),
                "event_type": row.get("event_type"),
                "created_at": row.get("created_at"),
                "processed_at": row.get("processed_at"),
                "status": (
                    row.get("status")
                    if row.get("status") in {"received", "processed", "failed"}
                    else "received"
                ),
                "error": row.get("error"),
            }
        )
        for row in rows
    ]
    return {"events": events}
