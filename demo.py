"""Send one payment notice and print its audit record."""

from decimal import Decimal
import json
import os

from campaign_service import FintechCampaign, PaymentEvent, RiskTier
from infrai_email import InfraiEmail


def main() -> None:
    recipient = os.environ.get("DEMO_EMAIL_TO")
    if not recipient:
        raise RuntimeError("DEMO_EMAIL_TO is required")
    event = PaymentEvent(
        event_id="pay-demo-001",
        customer_email=recipient,
        payment_reference="INV-2026-001",
        amount=Decimal("125.00"),
        currency="USD",
        risk_tier=RiskTier.LOW,
    )
    record = FintechCampaign(InfraiEmail()).notify_payment(event)
    print(json.dumps(record.to_dict(), indent=2))


if __name__ == "__main__":
    main()
