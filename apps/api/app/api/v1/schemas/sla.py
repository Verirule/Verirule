from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class OrgSlaRulesOut(BaseModel):
    org_id: UUID
    enabled: bool
    due_hours_low: int
    due_hours_medium: int
    due_hours_high: int
    due_soon_threshold_hours: int
    overdue_remind_every_hours: int
    created_at: datetime
    updated_at: datetime


class OrgSlaRulesUpdateIn(BaseModel):
    enabled: bool | None = None
    due_hours_low: int | None = Field(default=None, ge=1, le=24 * 365)
    due_hours_medium: int | None = Field(default=None, ge=1, le=24 * 365)
    due_hours_high: int | None = Field(default=None, ge=1, le=24 * 365)
    due_soon_threshold_hours: int | None = Field(default=None, ge=1, le=24 * 30)
    overdue_remind_every_hours: int | None = Field(default=None, ge=1, le=24 * 30)

    @model_validator(mode="after")
    def validate_due_order(self) -> "OrgSlaRulesUpdateIn":
        low = self.due_hours_low
        medium = self.due_hours_medium
        high = self.due_hours_high

        if low is not None and medium is not None and low < medium:
            raise ValueError("due_hours_low must be greater than or equal to due_hours_medium")
        if medium is not None and high is not None and medium < high:
            raise ValueError("due_hours_medium must be greater than or equal to due_hours_high")
        if low is not None and high is not None and low < high:
            raise ValueError("due_hours_low must be greater than or equal to due_hours_high")
        return self
