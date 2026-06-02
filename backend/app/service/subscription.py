from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import stripe
from sqlmodel import Session, select

from app.config import settings
from app.log import get_logger
from app.model.subscription import Subscription, SubscriptionStatus

logger = get_logger(__name__)

_PRODUCT_PRICES: dict[str, str] = {
    "pro": "price_pro_monthly",
    "pro_plus": "price_pro_plus_monthly",
}


class SubscriptionService:

    def __init__(self, session: Session) -> None:
        self._session = session
        stripe.api_key = settings.stripe_secret_key or ""

    def get_or_create(self, user_id: str) -> Subscription:
        sub = self._session.exec(
            select(Subscription).where(Subscription.user_id == UUID(user_id))
        ).first()
        if sub is None:
            sub = Subscription(user_id=UUID(user_id))
            self._session.add(sub)
            self._session.commit()
            self._session.refresh(sub)
        return sub

    def get_user_subscription(self, user_id: str) -> Subscription:
        return self.get_or_create(user_id)

    def get_tier(self, user_id: str) -> str:
        sub = self.get_or_create(user_id)
        return sub.tier.value if hasattr(sub.tier, "value") else str(sub.tier)

    def create_checkout_session(self, user_id: str, price_id: str, success_url: str, cancel_url: str) -> dict | None:
        if not stripe.api_key:
            return {
                "url": f"/mock-checkout?user_id={user_id}&tier={price_id}",
                "session_id": f"mock_{user_id}_{price_id}",
            }

        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,
                metadata={"user_id": user_id},
            )
            return {"url": session.url, "session_id": session.id}
        except stripe.error.StripeError as e:
            logger.error("stripe_checkout_failed", extra={"error": str(e)})
            return None

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        if not stripe.api_key:
            return {"status": "skipped", "message": "Stripe not configured"}

        endpoint_secret = settings.stripe_webhook_secret or ""

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except (ValueError, stripe.error.SignatureVerificationError) as e:
            logger.error("stripe_webhook_invalid", extra={"error": str(e)})
            return {"status": "error", "message": "Invalid signature"}

        event_type = event.get("type", "")
        data = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            self._handle_checkout_completed(data)
        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            self._handle_subscription_event(data, event_type)

        return {"status": "processed", "event": event_type}

    def _handle_checkout_completed(self, data: dict) -> None:
        user_id = data.get("metadata", {}).get("user_id", "")
        stripe_sub_id = data.get("subscription", "")
        stripe_customer_id = data.get("customer", "")

        if not user_id:
            return

        sub = self.get_or_create(user_id)
        sub.stripe_customer_id = stripe_customer_id
        sub.stripe_subscription_id = stripe_sub_id

        if data.get("mode") == "subscription":
            self._fetch_and_update_subscription(sub, stripe_sub_id)

        self._session.add(sub)
        self._session.commit()

    def _handle_subscription_event(self, data: dict, event_type: str) -> None:
        stripe_sub_id = data.get("id", "")
        if not stripe_sub_id:
            return

        existing = self._session.exec(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_sub_id
            )
        ).first()
        if existing is None:
            return

        status = data.get("status", "")
        if status in ("active", "trialing"):
            existing.status = SubscriptionStatus(status)
            if data.get("current_period_start"):
                existing.current_period_start = datetime.fromtimestamp(
                    data["current_period_start"], tz=timezone.utc
                )
            if data.get("current_period_end"):
                existing.current_period_end = datetime.fromtimestamp(
                    data["current_period_end"], tz=timezone.utc
                )
        elif status in ("canceled", "incomplete_expired"):
            existing.status = SubscriptionStatus.CANCELED
            if data.get("canceled_at"):
                existing.canceled_at = datetime.fromtimestamp(
                    data["canceled_at"], tz=timezone.utc
                )

        self._session.add(existing)
        self._session.commit()

    def _fetch_and_update_subscription(self, sub: Subscription, stripe_sub_id: str) -> None:
        try:
            stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
            items = stripe_sub.get("items", {}).get("data", [])
            if items:
                price_id = items[0].get("price", {}).get("id", "")
                tier = self._price_to_tier(price_id)
                if tier:
                    sub.tier = tier
            sub.current_period_start = datetime.fromtimestamp(
                stripe_sub["current_period_start"], tz=timezone.utc
            ) if stripe_sub.get("current_period_start") else None
            sub.current_period_end = datetime.fromtimestamp(
                stripe_sub["current_period_end"], tz=timezone.utc
            ) if stripe_sub.get("current_period_end") else None
        except stripe.error.StripeError as e:
            logger.warning("stripe_sub_retrieve_failed", extra={"error": str(e)})

    @staticmethod
    def _price_to_tier(price_id: str) -> str | None:
        mapping = {v: k for k, v in _PRODUCT_PRICES.items()}
        return mapping.get(price_id)

    def cancel_subscription(self, user_id: str) -> dict:
        sub = self.get_or_create(user_id)
        if not sub.stripe_subscription_id or not stripe.api_key:
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = datetime.now(timezone.utc)
            self._session.add(sub)
            self._session.commit()
            return {
                "status": "canceled",
                "message": "Subscription canceled (mock mode)",
                "effective_date": sub.canceled_at,
            }

        try:
            canceled = stripe.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = datetime.fromtimestamp(
                canceled.get("canceled_at", 0), tz=timezone.utc
            )
            self._session.add(sub)
            self._session.commit()
            return {
                "status": "canceled",
                "message": "Subscription will end at the current period",
                "effective_date": sub.canceled_at,
            }
        except stripe.error.StripeError as e:
            logger.error("stripe_cancel_failed", extra={"error": str(e)})
            return {"status": "error", "message": str(e), "effective_date": None}
