from dataclasses import asdict, dataclass
from enum import Enum
from typing import Literal


class Plan(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


FeatureName = Literal["integrations_enabled", "exports_enabled", "scheduling_enabled"]


@dataclass(frozen=True)
class PlanEntitlements:
    plan: Plan
    integrations_enabled: bool
    exports_enabled: bool
    scheduling_enabled: bool
    max_sources: int | None
    max_exports_per_month: int | None
    max_integrations: int | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def parse_plan(value: str | None) -> Plan:
    if value == Plan.PRO.value:
        return Plan.PRO
    if value == Plan.BUSINESS.value:
        return Plan.BUSINESS
    return Plan.FREE


def get_entitlements(plan: Plan | str | None) -> PlanEntitlements:
    resolved_plan = plan if isinstance(plan, Plan) else parse_plan(plan)

    if resolved_plan is Plan.BUSINESS:
        return PlanEntitlements(
            plan=resolved_plan,
            integrations_enabled=True,
            exports_enabled=True,
            scheduling_enabled=True,
            max_sources=None,
            max_exports_per_month=None,
            max_integrations=None,
        )

    if resolved_plan is Plan.PRO:
        return PlanEntitlements(
            plan=resolved_plan,
            integrations_enabled=True,
            exports_enabled=True,
            scheduling_enabled=True,
            max_sources=None,
            max_exports_per_month=500,
            max_integrations=10,
        )

    return PlanEntitlements(
        plan=Plan.FREE,
        integrations_enabled=False,
        exports_enabled=False,
        scheduling_enabled=False,
        max_sources=5,
        max_exports_per_month=5,
        max_integrations=0,
    )
