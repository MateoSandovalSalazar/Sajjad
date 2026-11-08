"""
Billing routes — Mercado Pago subscriptions.

GET  /billing/plans           → list all plans + pricing
POST /billing/checkout        → create MP checkout session
GET  /billing/subscription    → current user subscription
POST /billing/cancel          → cancel subscription
POST /billing/webhook         → MP event handler (public)
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header, Request
from sqlalchemy import select

from app.config import get_settings
from app.core.exceptions import (
    BillingDisabled,
    Forbidden,
    NotFound,
)
from app.core.limits import FREE_PLAN, PAID_PLANS, PLANS, get_limits
from app.dependencies import DB, VerifiedUser
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanCapabilities,
    PlanInfo,
    SubscriptionOut,
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


def _require_billing_enabled() -> None:
    """
    Puerta única de la pasarela de pagos.

    Mientras `billing_enabled` sea false el producto funciona entero
    (registro, trial, escaneos, PDF) pero no se cobra. Activar los
    pagos es poner las credenciales de MP y cambiar el flag — no hay
    que tocar ni una línea de esta lógica.
    """
    if not get_settings().billing_enabled:
        raise BillingDisabled(
            "Los pagos en línea todavía no están habilitados. "
            "Escríbenos para contratar un plan."
        )


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans():
    """Planes vendibles, en orden de precio."""
    return [
        PlanInfo.from_limits(name, PLANS[name]) for name in PAID_PLANS
    ]


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    payload: CheckoutRequest,
    user: VerifiedUser,
):
    _require_billing_enabled()

    if payload.plan not in PAID_PLANS:
        raise NotFound(f"Unknown plan: {payload.plan}")

    data = await create_subscription_checkout(
        user_id=str(user.id),
        user_email=user.email,
        plan=payload.plan,
    )
    return CheckoutResponse(**data)


@router.get("/subscription", response_model=SubscriptionOut)
async def get_my_subscription(user: VerifiedUser):
    sub = user.subscription
    if sub is None:
        raise NotFound("No subscription found.")

    plan = sub.effective_plan
    limits = get_limits(plan)

    return SubscriptionOut(
        id=sub.id,
        plan=plan,
        plan_label=limits.label or plan.capitalize(),
        status=sub.status.value,
        capabilities=PlanCapabilities.from_limits(limits),
        current_period_end=sub.current_period_end,
        scans_this_month=sub.scans_this_month,
        created_at=sub.created_at,
        is_trial=limits.is_trial,
        trial_ends_at=sub.trial_ends_at if limits.is_trial else None,
        trial_days_left=sub.trial_days_left(),
        billing_enabled=get_settings().billing_enabled,
    )


@router.post("/cancel", status_code=200)
async def cancel_my_subscription(user: VerifiedUser, db: DB):
    _require_billing_enabled()

    sub = user.subscription
    if sub is None or not sub.is_active:
        raise NotFound("No active subscription to cancel.")

    if sub.mp_subscription_id:
        await cancel_subscription(sub.mp_subscription_id)

    sub.status = SubscriptionStatus.CANCELLED
    sub.cancelled_at = datetime.now(timezone.utc)
    sub.plan = FREE_PLAN
    await db.commit()

    return {"message": "Subscription cancelled. Downgraded to free."}


@router.post("/webhook", status_code=200)
async def mercadopago_webhook(
    request: Request,
    db: DB,
    x_signature: str | None = Header(None),
    x_request_id: str | None = Header(None),
):
    """
    Recibe los eventos de Mercado Pago sobre cambios de suscripción.

    Este endpoint OTORGA PLANES, así que es el más sensible de la API:
    todo lo que no esté firmado con el secreto compartido se rechaza.
    """
    # Con los pagos apagados nadie legítimo llama aquí: se responde
    # 404 para no anunciar siquiera que la ruta existe.
    if not get_settings().billing_enabled:
        raise NotFound("Not found.")

    body = await request.body()

    # `data.id` viaja como query param y forma parte del manifest
    # firmado; sin él la verificación no puede reproducir el HMAC.
    data_id = request.query_params.get("data.id") or request.query_params.get(
        "id"
    )

    if not verify_webhook_signature(x_signature, x_request_id, data_id):
        logger.warning(
            "MP webhook: firma inválida (data.id=%s)", data_id
        )
        raise Forbidden("Invalid webhook signature.")

    try:
        data = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
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

    # external_reference lo generamos nosotros, pero llega de vuelta
    # desde MP: se valida antes de usarlo para consultar la BD.
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        logger.warning(
            "MP webhook: external_reference inválido: %r", external_ref
        )
        return

    if plan not in PAID_PLANS:
        logger.warning(
            "MP webhook: plan desconocido %r para user=%s", plan, user_id
        )
        return

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        return

    sub.mp_subscription_id = preapproval_id

    if mp_status == "authorized":
        sub.plan = plan
        sub.status = SubscriptionStatus.ACTIVE
        # Al pasar a un plan pagado la prueba deja de ser relevante,
        # pero conservamos la marca para no volver a otorgarla.
        sub.cancelled_at = None
        logger.info(
            "Subscription activated: user=%s plan=%s",
            user_id_str,
            plan,
        )
    elif mp_status in ("cancelled", "paused"):
        sub.status = SubscriptionStatus.CANCELLED
        sub.plan = FREE_PLAN
        sub.cancelled_at = datetime.now(timezone.utc)
        logger.info(
            "Subscription cancelled: user=%s", user_id_str
        )

    await db.commit()
