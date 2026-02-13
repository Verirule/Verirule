from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

BillingPlan = Literal["free", "pro", "business"]
BillingPlanStatus = Literal["active", "past_due", "canceled", "trialing"]


class BillingOut(BaseModel):
    org_id: UUID
    plan: BillingPlan
    plan_status: BillingPlanStatus
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    current_period_end: datetime | None
    entitlements: dict[str, object]


class BillingEventOut(BaseModel):
    id: UUID
    org_id: UUID
    stripe_event_id: str
    event_type: str
    created_at: datetime
    processed_at: datetime | None
    status: Literal["received", "processed", "failed"]
    error: str | None
