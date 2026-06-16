"""
Billing routes — Mercado Pago subscriptions.

GET  /billing/plans           → list all plans + pricing
POST /billing/checkout        → create MP checkout session
GET  /billing/subscription    → current user subscription
POST /billing/cancel          → cancel subscription
POST /billing/webhook         → MP event handler (public)
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Header, Request
from sqlalchemy import select

from app.config import get_settings
from app.core.exceptions import Forbidden, NotFound
from app.core.limits import MP_PLAN_PRICES, PLANS
from app.dependencies import DB, VerifiedUser
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanInfo,
    SubscriptionOut,
    WebhookPayload,
)
from app.services.mercadopago import (
    cancel_subscription,
    create_subscription_checkout,
    get_subscription,
    parse_webhook_event,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans():
    return [
        PlanInfo(
            name=name,
            price_usd=limits.price_usd,
            max_domains=limits.max_domains,
            max_scans_per_month=limits.max_scans_per_month,
            scan_interval_days=limits.scan_interval_days,
            can_download_pdf=limits.can_download_pdf,
            white_label=limits.white_label,
        )
        for name, limits in PLANS.items()
        if name != "free"
    ]


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    user: VerifiedUser,
):
    if payload.plan not in ("starter", "professional", "agency"):
        from app.core.exceptions import NotFound as NF

        raise NF(f"Unknown plan: {payload.plan}")

    data = await create_subscription_checkout(
        user_id=str(user.id),
        user_email=user.email,
        plan=payload.plan,
    )
    return CheckoutResponse(**data)


@router.get("/subscription", response_model=SubscriptionOut)
async def get_my_subscription(user: VerifiedUser, db: DB):
    if not user.subscription:
        raise NotFound("No subscription found.")
    return user.subscription


@router.post("/cancel", status_code=200)
async def cancel_my_subscription(user: VerifiedUser, db: DB):
    sub = user.subscription
    if sub is None or not sub.is_active:
        raise NotFound("No active subscription to cancel.")

    if sub.mp_subscription_id:
        await cancel_subscription(sub.mp_subscription_id)

    sub.status = SubscriptionStatus.CANCELLED
    sub.cancelled_at = datetime.now(timezone.utc)
    sub.plan = "free"
    await db.flush()

    return {"message": "Subscription cancelled. Downgraded to free."}


@router.post("/webhook", status_code=200)
async def mercadopago_webhook(
    request: Request,
    db: DB,
    x_signature: str | None = Header(None),
    x_request_id: str | None = Header(None),
):
    """
    Mercado Pago sends POST events here on subscription changes.
    We verify the signature and update the DB accordingly.
    """
    body = await request.body()

    if not verify_webhook_signature(x_signature, x_request_id, body):
        logger.warning("MP webhook: invalid signature")
        raise Forbidden("Invalid webhook signature.")

    try:
        import json

        data = json.loads(body)
    except Exception:
        return {"status": "ignored"}

    event = parse_webhook_event(data)
    if event is None:
        return {"status": "ignored"}

    if event["kind"] == "subscription":
        await _handle_subscription_event(event, db)

    return {"status": "ok"}


async def _handle_subscription_event(event: dict, db: DB) -> None:
    preapproval_id = event.get("preapproval_id")
    if not preapproval_id:
        return

    try:
        mp_data = await get_subscription(preapproval_id)
    except Exception as exc:
        logger.warning("Could not fetch MP sub %s: %s", preapproval_id, exc)
        return

    external_ref = mp_data.get("external_reference", "")
    if ":" not in external_ref:
        return

    user_id_str, plan = external_ref.split(":", 1)
    mp_status = mp_data.get("status", "")

    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == __import__(
                "uuid", fromlist=["UUID"]
            ).UUID(user_id_str)
        )
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return

    sub.mp_subscription_id = preapproval_id

    if mp_status == "authorized":
        sub.plan = plan
        sub.status = SubscriptionStatus.ACTIVE
        logger.info(
            "Subscription activated: user=%s plan=%s",
            user_id_str,
            plan,
        )
    elif mp_status in ("cancelled", "paused"):
        sub.status = SubscriptionStatus.CANCELLED
        sub.plan = "free"
        sub.cancelled_at = datetime.now(timezone.utc)
        logger.info(
            "Subscription cancelled: user=%s", user_id_str
        )

    await db.flush()
