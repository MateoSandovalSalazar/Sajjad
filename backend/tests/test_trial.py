"""
Tests de la prueba gratuita.

Cubre las tres piezas: el otorgamiento al verificar el email, la
degradación perezosa cuando la fecha pasó (el request no puede
esperar al beat) y la unicidad — una cuenta consume su trial una
sola vez.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from tests.conftest import API, auth_headers

pytestmark = pytest.mark.asyncio


async def _register(client, email="trial@example.com"):
    r = await client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": "Tormenta7Azul",
            "full_name": "Trial User",
        },
    )
    assert r.status_code == 201, r.text
    return r


async def _token_for(db, email):
    res = await db.execute(select(User).where(User.email == email))
    return res.scalar_one().email_verification_token


async def _sub_for(db, email):
    res = await db.execute(
        select(Subscription)
        .join(User)
        .where(User.email == email)
    )
    return res.scalar_one()


async def _login(client, email):
    r = await client.post(
        f"{API}/auth/login",
        json={"email": email, "password": "Tormenta7Azul"},
    )
    assert r.status_code == 200, r.text
    return r.json()


async def test_register_starts_on_free(client, db):
    """El trial NO se otorga al registrarse, sólo al verificar."""
    await _register(client)
    sub = await _sub_for(db, "trial@example.com")
    assert sub.plan == "free"
    assert sub.trial_ends_at is None


async def test_verify_email_grants_trial(client, db):
    await _register(client)
    token = await _token_for(db, "trial@example.com")

    r = await client.get(f"{API}/auth/verify-email?token={token}")
    assert r.status_code == 200

    await db.commit()
    sub = await _sub_for(db, "trial@example.com")
    await db.refresh(sub)
    assert sub.plan == "trial"
    assert sub.trial_ends_at is not None
    assert sub.status == SubscriptionStatus.ACTIVE


async def test_trial_unlocks_findings_and_pdf(client, db):
    """La prueba sirve para algo: desbloquea el producto real."""
    await _register(client)
    token = await _token_for(db, "trial@example.com")
    await client.get(f"{API}/auth/verify-email?token={token}")

    tokens = await _login(client, "trial@example.com")
    r = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    body = r.json()
    assert body["plan"] == "trial"
    assert body["is_trial"] is True
    assert body["capabilities"]["can_see_findings"] is True
    assert body["capabilities"]["can_download_pdf"] is True
    assert 0 < body["trial_days_left"] <= 14


async def test_expired_trial_reports_free_without_beat(client, db):
    """
    Degradación perezosa: el beat corre una vez al día, así que la
    expiración debe notarse en el request siguiente, no 24 h después.
    """
    await _register(client)
    token = await _token_for(db, "trial@example.com")
    await client.get(f"{API}/auth/verify-email?token={token}")
    await db.commit()

    sub = await _sub_for(db, "trial@example.com")
    sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
    await db.commit()

    tokens = await _login(client, "trial@example.com")
    r = await client.get(
        f"{API}/billing/subscription", headers=auth_headers(tokens)
    )
    body = r.json()
    assert body["plan"] == "free"
    assert body["capabilities"]["can_see_findings"] is False


async def test_expired_trial_blocks_findings_endpoint(client, db):
    """La degradación se aplica de verdad, no sólo en la respuesta."""
    await _register(client)
    token = await _token_for(db, "trial@example.com")
    await client.get(f"{API}/auth/verify-email?token={token}")
    await db.commit()

    sub = await _sub_for(db, "trial@example.com")
    sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
    await db.commit()

    tokens = await _login(client, "trial@example.com")
    # Segundo dominio: el plan free sólo permite 1.
    for i, fqdn in enumerate(["uno.com", "dos.com"]):
        r = await client.post(
            f"{API}/domains",
            json={"fqdn": fqdn, "authorized": True},
            headers=auth_headers(tokens),
        )
        expected = 201 if i == 0 else 402
        assert r.status_code == expected, r.text


async def test_trial_granted_only_once(client, db):
    """
    Reverificar el email no recicla la prueba: `trial_ends_at` queda
    como marca de que esa cuenta ya la consumió.
    """
    await _register(client)
    token = await _token_for(db, "trial@example.com")
    await client.get(f"{API}/auth/verify-email?token={token}")
    await db.commit()

    sub = await _sub_for(db, "trial@example.com")
    original_end = sub.trial_ends_at

    # Simula el fin del trial y un intento de re-otorgamiento.
    sub.plan = "free"
    sub.email_verification_token = None
    await db.commit()

    from app.services.auth import _start_trial

    _start_trial(sub)
    assert sub.plan == "free"
    assert sub.trial_ends_at == original_end


async def test_paid_plan_keeps_its_plan(client, db):
    """_start_trial nunca pisa un plan de pago."""
    await _register(client)
    sub = await _sub_for(db, "trial@example.com")
    sub.plan = "professional"
    await db.commit()

    from app.services.auth import _start_trial

    _start_trial(sub)
    assert sub.plan == "professional"
    assert sub.trial_ends_at is None
