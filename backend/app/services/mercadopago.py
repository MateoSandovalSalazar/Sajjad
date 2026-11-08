"""
Mercado Pago integration — subscriptions (preapproval).

Supports: Argentina, Brasil, Chile, Colombia, México, Perú,
Uruguay — all countries where MP operates.

Flow:
1. POST /billing/checkout → create preapproval preference
2. User completes payment on MP → redirect to frontend
3. MP fires webhook → POST /billing/webhook → activate sub

Docs: https://www.mercadopago.com.ar/developers/es/docs/subscriptions
"""

import hashlib
import hmac
import logging
import time
import uuid

import httpx

from app.config import get_settings
from app.core.limits import PAID_PLANS, PLANS

logger = logging.getLogger(__name__)

_MP_API = "https://api.mercadopago.com"

# Antigüedad máxima aceptada para el timestamp de un webhook.
_WEBHOOK_MAX_AGE_SECONDS = 300


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.mp_access_token}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": str(uuid.uuid4()),
    }


async def create_subscription_checkout(
    user_id: str,
    user_email: str,
    plan: str,
) -> dict:
    """
    Creates a Mercado Pago preapproval (subscription) and
    returns the checkout URL + preapproval ID.
    """
    settings = get_settings()

    # Los precios viven en core/limits.py (fuente única de verdad).
    # MP se encarga de la conversión de moneda desde USD.
    if plan not in PAID_PLANS:
        raise ValueError(f"Unknown plan: {plan}")

    amount = PLANS[plan].price_usd
    back_url = f"{settings.frontend_url}/billing/success"

    payload = {
        "reason": f"Sajjad — Plan {plan.capitalize()}",
        "external_reference": f"{user_id}:{plan}",
        "payer_email": user_email,
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": amount,
            "currency_id": "USD",
        },
        "back_url": back_url,
        "status": "pending",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_MP_API}/preapproval",
            json=payload,
            headers=_headers(),
        )
        resp.raise_for_status()
        data = resp.json()

    logger.info(
        "MP preapproval created for user %s, plan %s: %s",
        user_id,
        plan,
        data.get("id"),
    )

    return {
        "checkout_url": data["init_point"],
        "preference_id": data["id"],
    }


async def get_subscription(preapproval_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{_MP_API}/preapproval/{preapproval_id}",
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def cancel_subscription(preapproval_id: str) -> bool:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{_MP_API}/preapproval/{preapproval_id}",
            json={"status": "cancelled"},
            headers=_headers(),
        )
        return resp.status_code == 200


def verify_webhook_signature(
    signature_header: str | None,
    request_id_header: str | None,
    data_id: str | None,
) -> bool:
    """
    Valida la firma HMAC-SHA256 del webhook de Mercado Pago.

    MP envía la cabecera `x-signature: ts=<epoch>,v1=<hmac>` y firma
    este manifest exacto:

        id:<data.id>;request-id:<x-request-id>;ts:<ts>;

    donde `data.id` es el query param de la URL de notificación (NO
    la cabecera x-request-id). El cuerpo del POST no entra en el
    manifest.

    Docs: https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks
    """
    settings = get_settings()

    # Fail-closed. Sin secreto NO se valida nada, y este endpoint es
    # el que otorga planes: aceptar sin firma dejaría que cualquiera
    # se auto-asigne el plan Agency con un POST. Si falta el secreto,
    # se rechaza todo.
    if not settings.mp_webhook_secret:
        logger.error(
            "MP_WEBHOOK_SECRET no configurado — se rechaza el webhook. "
            "Sin secreto no se puede verificar el origen del evento."
        )
        return False

    if not signature_header:
        return False

    parts = dict(
        part.strip().split("=", 1)
        for part in signature_header.split(",")
        if "=" in part
    )
    ts = parts.get("ts", "")
    v1 = parts.get("v1", "")

    if not ts or not v1:
        return False

    # Rechaza eventos viejos para acotar la ventana de replay: un
    # webhook capturado no debe poder reenviarse horas después.
    try:
        age = abs(time.time() - int(ts))
    except ValueError:
        return False
    if age > _WEBHOOK_MAX_AGE_SECONDS:
        logger.warning(
            "MP webhook rechazado: timestamp con %.0fs de antigüedad",
            age,
        )
        return False

    # MP normaliza el data.id alfanumérico a minúsculas antes de firmar.
    normalized_id = (data_id or "").lower()

    manifest = (
        f"id:{normalized_id};"
        f"request-id:{request_id_header or ''};"
        f"ts:{ts};"
    )

    expected = hmac.new(
        settings.mp_webhook_secret.encode(),
        manifest.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, v1)


def parse_webhook_event(payload: dict) -> dict | None:
    """
    Extracts meaningful info from a MP webhook payload.
    Returns None for events we don't handle.
    """
    event_type = payload.get("type")
    action = payload.get("action")
    data = payload.get("data") or {}

    if event_type == "subscription_preapproval":
        return {
            "kind": "subscription",
            "action": action,
            "preapproval_id": data.get("id"),
        }

    if event_type == "payment":
        return {
            "kind": "payment",
            "action": action,
            "payment_id": data.get("id"),
        }

    return None
