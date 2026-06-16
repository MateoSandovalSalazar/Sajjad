import uuid
from datetime import datetime

from pydantic import BaseModel


class PlanInfo(BaseModel):
    name: str
    price_usd: int
    max_domains: int
    max_scans_per_month: int
    scan_interval_days: int | None
    can_download_pdf: bool
    white_label: bool


class CheckoutRequest(BaseModel):
    plan: str  # starter | professional | agency


class CheckoutResponse(BaseModel):
    checkout_url: str
    preference_id: str


class SubscriptionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    plan: str
    status: str
    current_period_end: datetime | None
    scans_this_month: int
    created_at: datetime


class WebhookPayload(BaseModel):
    """Mercado Pago webhook body (flexible — MP can change fields)."""

    model_config = {"extra": "allow"}

    action: str | None = None
    type: str | None = None
    data: dict | None = None
