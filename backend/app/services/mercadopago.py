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
import uuid

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_MP_API = "https://api.mercadopago.com"
_PLAN_PREAPPROVAL_IDS: dict[str, str] = {}  # populated from settings


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

    # Price map in USD (MP handles currency conversion)
    plan_prices = {
        "starter": {"amount": 30, "currency": "USD"},
        "professional": {"amount": 50, "currency": "USD"},
        "agency": {"amount": 120, "currency": "USD"},
    }
    if plan not in plan_prices:
        raise ValueError(f"Unknown plan: {plan}")

    price = plan_prices[plan]
    back_url = f"{settings.frontend_url}/billing/success"

    payload = {
        "reason": f"Sajjad — Plan {plan.capitalize()}",
        "external_reference": f"{user_id}:{plan}",
        "payer_email": user_email,
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": price["amount"],
            "currency_id": price["currency"],
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
    payload_bytes: bytes,
) -> bool:
    """
    Validates MP webhook HMAC-SHA256 signature.

    MP sends: x-signature: ts=...,v1=...
    We build: ts + "." + request_id + "." + body_hash
    """
    settings = get_settings()
    if not settings.mp_webhook_secret:
        logger.warning(
            "MP_WEBHOOK_SECRET not set — skipping signature check"
        )
        return True

    if not signature_header:
        return False

    parts = dict(
        part.split("=", 1)
        for part in signature_header.split(",")
        if "=" in part
    )
    ts = parts.get("ts", "")
    v1 = parts.get("v1", "")

    body_hash = hashlib.sha256(payload_bytes).hexdigest()
    manifest = f"id:{request_id_header};request-id:{ts};ts:{ts};"
    # MP's actual manifest format:
    manifest = (
        f"id:{request_id_header};"
        f"request-id:{request_id_header};"
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
