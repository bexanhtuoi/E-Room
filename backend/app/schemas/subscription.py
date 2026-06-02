from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    trial_ends_at: datetime | None = None
    current_period_end: datetime | None = None
    canceled_at: datetime | None = None
    stripe_customer_id: str | None = None


class CheckoutResponse(BaseModel):
    url: str
    session_id: str


class CancelResponse(BaseModel):
    status: str
    message: str
    effective_date: datetime | None = None


class InvoiceResponse(BaseModel):
    id: str
    amount: int
    currency: str
    status: str
    date: datetime | None = None
    pdf_url: str | None = None


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
