from dataclasses import dataclass
from typing import Literal

IntegrationType = Literal["slack", "jira", "github"]


@dataclass(frozen=True)
class AlertNotification:
    alert_id: str
    org_id: str
    finding_id: str
    title: str
    summary: str
    severity: Literal["low", "medium", "high", "critical"]
