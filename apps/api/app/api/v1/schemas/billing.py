from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

BillingPlan = Literal["free", "pro", "business"]


class BillingOut(BaseModel):
    org_id: UUID
    plan: BillingPlan
    subscription_status: str | None
    current_period_end: datetime | None
