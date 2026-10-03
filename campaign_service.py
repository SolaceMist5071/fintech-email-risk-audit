"""Payment-event notifications and their risk-sensitive follow-up decision."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from infrai_email import InfraiEmail


class RiskTier(str, Enum):
    LOW = "low"
    HIGH = "high"


class CampaignAction(str, Enum):
    RECORD_ENGAGEMENT = "record_engagement"
    CONTINUE_MONITORING = "continue_monitoring"
    PAUSE_AND_REVIEW = "pause_and_review"


@dataclass(frozen=True)
class PaymentEvent:
    event_id: str
    customer_email: str
    payment_reference: str
    amount: Decimal
    currency: str
    risk_tier: RiskTier


@dataclass(frozen=True)
class AuditRecord:
    event_id: str
    message_id: str
    action: CampaignAction
    reason: str
    observed_at: str

    def to_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}


class FintechCampaign:
    def __init__(self, email: InfraiEmail) -> None:
        self.email = email

    def notify_payment(self, event: PaymentEvent) -> AuditRecord:
        text = (
            f"Payment reference: {event.payment_reference}\n"
            f"Amount: {event.amount} {event.currency}\n"
            f"Audit event: {event.event_id}"
        )
        result = self.email.send_payment_notice(
            to=event.customer_email,
            subject=f"Payment update {event.payment_reference}",
            text=text,
            event_id=event.event_id,
        )
        return AuditRecord(
            event_id=event.event_id,
            message_id=str(result["message_id"]),
            action=CampaignAction.CONTINUE_MONITORING,
            reason="notification_sent",
            observed_at=_now(),
        )

    def assess_delivery(
        self, *, event_id: str, message_id: str, risk_tier: RiskTier
    ) -> AuditRecord:
        response = self.email.list_events(message_id)
        events = _event_items(response)
        kinds = {str(item.get("type", "")).lower() for item in events}
        if "bounce" in kinds or "bounced" in kinds:
            action = CampaignAction.PAUSE_AND_REVIEW
            reason = "delivery_bounced"
        elif "open" in kinds or "opened" in kinds:
            action = CampaignAction.RECORD_ENGAGEMENT
            reason = "message_opened"
        elif risk_tier is RiskTier.HIGH:
            action = CampaignAction.PAUSE_AND_REVIEW
            reason = "high_risk_without_open"
        else:
            action = CampaignAction.CONTINUE_MONITORING
            reason = "awaiting_engagement"
        return AuditRecord(event_id, message_id, action, reason, _now())


def _event_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    candidate = response.get("events", response.get("items", []))
    return [item for item in candidate if isinstance(item, dict)]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
