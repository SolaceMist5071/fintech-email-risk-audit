"""Typed HTTP entry point for the fintech campaign example."""

from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from campaign_service import FintechCampaign, PaymentEvent, RiskTier
from infrai_email import InfraiEmail, InfraiError


app = FastAPI(title="Fintech campaign event service")


class PaymentNoticeRequest(BaseModel):
    event_id: str = Field(min_length=1)
    customer_email: EmailStr
    payment_reference: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    risk_tier: RiskTier


class DeliveryAssessmentRequest(BaseModel):
    event_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    risk_tier: RiskTier


def campaign() -> FintechCampaign:
    return FintechCampaign(InfraiEmail())


@app.post("/payment-notices")
def create_payment_notice(request: PaymentNoticeRequest) -> dict[str, str]:
    try:
        return campaign().notify_payment(PaymentEvent(**request.model_dump())).to_dict()
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.code) from exc


@app.post("/delivery-assessments")
def create_delivery_assessment(request: DeliveryAssessmentRequest) -> dict[str, str]:
    try:
        return campaign().assess_delivery(**request.model_dump()).to_dict()
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail=exc.code) from exc
