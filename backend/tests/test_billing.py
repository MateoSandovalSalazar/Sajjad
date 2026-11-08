"""Tests de billing (sin tocar Mercado Pago real)."""

import pytest

from tests.conftest import API, auth_headers, register_and_verify

pytestmark = pytest.mark.asyncio


async def test_get_subscription_returns_free(client, db):
    _, tokens = await register_and_verify(client, db)
    r = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "free"
    assert body["scans_this_month"] == 0


async def test_subscription_requires_auth(client):
    r = await client.get(f"{API}/billing/subscription")
    assert r.status_code == 401


async def test_checkout_unknown_plan_rejected(client, db, billing_on):
    _, tokens = await register_and_verify(client, db)
    r = await client.post(
        f"{API}/billing/checkout",
        json={"plan": "platinum"},
        headers=auth_headers(tokens),
    )
    assert r.status_code == 404


async def test_cancel_downgrades_to_free(client, db, billing_on):
    _, tokens = await register_and_verify(
        client, db, plan="professional"
    )
    r = await client.post(
        f"{API}/billing/cancel", headers=auth_headers(tokens)
    )
    assert r.status_code == 200

    sub = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    assert sub.json()["plan"] == "free"
    assert sub.json()["status"] == "cancelled"


# ── Pasarela apagada (estado actual del producto) ───────────


async def test_checkout_disabled_returns_503(client, db):
    """Sin pagos activos, el checkout falla de forma clara y no 500."""
    _, tokens = await register_and_verify(client, db)
    r = await client.post(
        f"{API}/billing/checkout",
        json={"plan": "professional"},
        headers=auth_headers(tokens),
    )
    assert r.status_code == 503
    assert r.json()["error"] == "BillingDisabled"


async def test_cancel_disabled_returns_503(client, db):
    _, tokens = await register_and_verify(
        client, db, plan="professional"
    )
    r = await client.post(
        f"{API}/billing/cancel", headers=auth_headers(tokens)
    )
    assert r.status_code == 503


async def test_subscription_reports_billing_flag(client, db):
    """El frontend usa este flag para ocultar el botón de mejorar."""
    _, tokens = await register_and_verify(client, db)
    r = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    assert r.json()["billing_enabled"] is False


async def test_subscription_exposes_capabilities(client, db):
    """
    Las capacidades viajan en la respuesta: el frontend no reimplementa
    la tabla de límites, así que no puede desincronizarse.
    """
    _, tokens = await register_and_verify(
        client, db, plan="professional"
    )
    r = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    caps = r.json()["capabilities"]
    assert caps["max_domains"] == 3
    assert caps["can_see_findings"] is True
    assert caps["can_download_pdf"] is True


async def test_plans_endpoint_only_lists_sellable_plans(client):
    r = await client.get(f"{API}/billing/plans")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert names == ["starter", "professional", "agency"]
    assert all("capabilities" in p for p in r.json())
