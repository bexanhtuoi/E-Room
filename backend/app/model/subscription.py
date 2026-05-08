from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from app.model.common import BaseEntity, SubscriptionTier


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


class Subscription(BaseEntity):
    user_id: str
    tier: SubscriptionTier = SubscriptionTier.FREE
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    trial_ends_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    canceled_at: datetime | None = None
