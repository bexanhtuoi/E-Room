from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.api.dependencies import get_current_user, get_db_session
from app.config import settings
from app.schemas.subscription import (
    CancelResponse,
    CheckoutResponse,
    InvoiceListResponse,
    InvoiceResponse,
    SubscriptionResponse,
)
from app.service.subscription import SubscriptionService

router = APIRouter()


def _sub_to_response(sub) -> SubscriptionResponse:
    return SubscriptionResponse(
        tier=sub.tier.value if hasattr(sub.tier, "value") else str(sub.tier),
        status=sub.status.value if hasattr(sub.status, "value") else str(sub.status),
        trial_ends_at=sub.trial_ends_at,
        current_period_end=sub.current_period_end,
        canceled_at=sub.canceled_at,
        stripe_customer_id=sub.stripe_customer_id,
    )


@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> SubscriptionResponse:
    service = SubscriptionService(session)
    sub = service.get_user_subscription(current_user["id"])
    return _sub_to_response(sub)


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    tier: str = "pro",
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> CheckoutResponse:
    valid_tiers = {"pro": "price_pro_monthly", "pro_plus": "price_pro_plus_monthly"}
    if tier not in valid_tiers:
        raise HTTPException(status_code=400, detail=f"Invalid tier. Valid: {', '.join(valid_tiers)}")

    service = SubscriptionService(session)
    frontend_url = settings.frontend_url
    result = service.create_checkout_session(
        user_id=current_user["id"],
        price_id=valid_tiers[tier],
        success_url=f"{frontend_url}/settings/billing?success=1",
        cancel_url=f"{frontend_url}/settings/billing?canceled=1",
    )

    if result is None:
        raise HTTPException(status_code=500, detail="Failed to create checkout session")

    return CheckoutResponse(url=result["url"], session_id=result["session_id"])


@router.post("/cancel", response_model=CancelResponse)
async def cancel_subscription(
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> CancelResponse:
    service = SubscriptionService(session)
    result = service.cancel_subscription(current_user["id"])

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Cancel failed"))

    return CancelResponse(
        status=result.get("status", "canceled"),
        message=result.get("message", ""),
        effective_date=result.get("effective_date"),
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, session: Session = Depends(get_db_session)) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    service = SubscriptionService(session)
    return service.handle_webhook(payload, sig_header)


@router.get("/invoices", response_model=InvoiceListResponse)
async def list_invoices(
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> InvoiceListResponse:
    service = SubscriptionService(session)
    sub = service.get_user_subscription(current_user["id"])

    if not sub.stripe_customer_id:
        return InvoiceListResponse(items=[])

    import stripe

    try:
        stripe.api_key = settings.stripe_secret_key or ""
        invoice_list = stripe.Invoice.list(customer=sub.stripe_customer_id, limit=10)
        items = [
            InvoiceResponse(
                id=inv.get("id", ""),
                amount=inv.get("amount_paid", inv.get("total", 0)),
                currency=inv.get("currency", "usd"),
                status=inv.get("status", "unknown"),
                date=datetime.fromtimestamp(inv.get("created", 0), tz=timezone.utc) if inv.get("created") else None,
                pdf_url=inv.get("invoice_pdf"),
            )
            for inv in invoice_list.get("data", [])
        ]
        return InvoiceListResponse(items=items)
    except Exception:
        return InvoiceListResponse(items=[])
