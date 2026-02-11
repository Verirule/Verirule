from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.schemas.billing import BillingOut
from app.core.supabase_jwt import VerifiedSupabaseAuth, verify_supabase_auth
from app.core.supabase_rest import select_org_billing

router = APIRouter()
supabase_auth_dependency = Depends(verify_supabase_auth)


@router.get("/billing")
async def billing(
    org_id: UUID, auth: VerifiedSupabaseAuth = supabase_auth_dependency
) -> BillingOut:
    row = await select_org_billing(auth.access_token, str(org_id))
    if row is None:
        return BillingOut.model_validate(
            {
                "org_id": str(org_id),
                "plan": "free",
                "subscription_status": "inactive",
                "current_period_end": None,
            }
        )

    plan = row.get("plan")
    if plan not in {"free", "pro", "business"}:
        plan = "free"

    return BillingOut.model_validate(
        {
            "org_id": row.get("org_id") or str(org_id),
            "plan": plan,
            "subscription_status": row.get("subscription_status"),
            "current_period_end": row.get("current_period_end"),
        }
    )
