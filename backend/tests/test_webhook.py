"""
Tests del endpoint webhook de Mercado Pago: activa/cancela la
suscripción según el evento. Se mockea la firma y la llamada al
SDK de MP (`get_subscription`) — sin red.
"""

import pytest

from app.routers import billing
from tests.conftest import API, auth_headers, register_and_verify

pytestmark = pytest.mark.asyncio

WEBHOOK = f"{API}/billing/webhook"


def _mp_data(user_id, plan, status):
    async def _fake_get_subscription(preapproval_id):
        return {
            "external_reference": f"{user_id}:{plan}",
            "status": status,
        }

    return _fake_get_subscription


async def test_webhook_invalid_signature_403(
    client, monkeypatch, billing_on
):
    monkeypatch.setattr(
        billing, "verify_webhook_signature", lambda *a, **k: False
    )
    r = await client.post(
        WEBHOOK,
        json={"type": "subscription_preapproval", "data": {"id": "x"}},
    )
    assert r.status_code == 403


async def test_webhook_activates_subscription(
    client, db, monkeypatch, billing_on
):
    user, tokens = await register_and_verify(client, db)
    monkeypatch.setattr(
        billing, "verify_webhook_signature", lambda *a, **k: True
    )
    monkeypatch.setattr(
        billing,
        "get_subscription",
        _mp_data(user.id, "professional", "authorized"),
    )

    r = await client.post(
        WEBHOOK,
        json={
            "type": "subscription_preapproval",
            "action": "updated",
            "data": {"id": "preapp-1"},
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    sub = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    body = sub.json()
    assert body["plan"] == "professional"
    assert body["status"] == "active"


async def test_webhook_cancels_subscription(
    client, db, monkeypatch, billing_on
):
    user, tokens = await register_and_verify(
        client, db, plan="professional"
    )
    monkeypatch.setattr(
        billing, "verify_webhook_signature", lambda *a, **k: True
    )
    monkeypatch.setattr(
        billing,
        "get_subscription",
        _mp_data(user.id, "professional", "cancelled"),
    )

    r = await client.post(
        WEBHOOK,
        json={
            "type": "subscription_preapproval",
            "action": "updated",
            "data": {"id": "preapp-1"},
        },
    )
    assert r.status_code == 200

    sub = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    body = sub.json()
    assert body["plan"] == "free"
    assert body["status"] == "cancelled"


async def test_webhook_ignores_unknown_event(
    client, monkeypatch, billing_on
):
    monkeypatch.setattr(
        billing, "verify_webhook_signature", lambda *a, **k: True
    )
    r = await client.post(
        WEBHOOK, json={"type": "topic_merchant_order"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


async def test_webhook_closed_when_billing_disabled(
    client, db, monkeypatch
):
    """
    Sin billing_on la pasarela está apagada: el webhook responde 404
    ANTES de mirar la firma. Es el endpoint que otorga planes, así que
    mientras no se cobre no debe existir para el mundo.
    """
    user, tokens = await register_and_verify(client, db)
    monkeypatch.setattr(
        billing, "verify_webhook_signature", lambda *a, **k: True
    )
    monkeypatch.setattr(
        billing,
        "get_subscription",
        _mp_data(user.id, "agency", "authorized"),
    )

    r = await client.post(
        WEBHOOK,
        json={
            "type": "subscription_preapproval",
            "action": "updated",
            "data": {"id": "preapp-1"},
        },
    )
    assert r.status_code == 404

    # Y el plan del usuario no cambió.
    sub = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    assert sub.json()["plan"] == "free"
