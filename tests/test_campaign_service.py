from campaign_service import CampaignAction, FintechCampaign, RiskTier


class EventClient:
    def __init__(self, event_type: str) -> None:
        self.event_type = event_type

    def list_events(self, message_id: str) -> dict[str, object]:
        return {"events": [{"type": self.event_type, "message_id": message_id}]}


def test_bounce_pauses_even_a_low_risk_campaign() -> None:
    service = FintechCampaign(EventClient("bounced"))  # type: ignore[arg-type]

    record = service.assess_delivery(
        event_id="pay-42", message_id="msg-42", risk_tier=RiskTier.LOW
    )

    assert record.action is CampaignAction.PAUSE_AND_REVIEW
    assert record.reason == "delivery_bounced"


def test_high_risk_payment_without_open_is_paused() -> None:
    service = FintechCampaign(EventClient("delivered"))  # type: ignore[arg-type]

    record = service.assess_delivery(
        event_id="pay-43", message_id="msg-43", risk_tier=RiskTier.HIGH
    )

    assert record.action is CampaignAction.PAUSE_AND_REVIEW
    assert record.reason == "high_risk_without_open"
