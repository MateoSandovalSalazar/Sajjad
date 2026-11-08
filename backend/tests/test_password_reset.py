"""
Tests del flujo de recuperación de contraseña:
forgot-password → token en BD → reset-password → login nuevo.
"""

import pytest
from sqlalchemy import select

from app.models.user import User
from tests.conftest import API

pytestmark = pytest.mark.asyncio

USER = {
    "email": "reset@example.com",
    "password": "Tormenta7Azul",
    "full_name": "R",
}


async def _reset_token(db, email):
    db.expire_all()
    res = await db.execute(select(User).where(User.email == email))
    return res.scalar_one().password_reset_token


async def test_full_reset_flow(client, db):
    await client.post(f"{API}/auth/register", json=USER)

    r = await client.post(
        f"{API}/auth/forgot-password", json={"email": USER["email"]}
    )
    assert r.status_code == 202

    token = await _reset_token(db, USER["email"])
    assert token

    new_password = "BrandNew99"
    rr = await client.post(
        f"{API}/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert rr.status_code == 200

    # La contraseña nueva funciona...
    ok = await client.post(
        f"{API}/auth/login",
        json={"email": USER["email"], "password": new_password},
    )
    assert ok.status_code == 200

    # ...y la vieja ya no.
    bad = await client.post(
        f"{API}/auth/login",
        json={"email": USER["email"], "password": USER["password"]},
    )
    assert bad.status_code == 401


async def test_reset_token_single_use(client, db):
    await client.post(f"{API}/auth/register", json=USER)
    await client.post(
        f"{API}/auth/forgot-password", json={"email": USER["email"]}
    )
    token = await _reset_token(db, USER["email"])

    first = await client.post(
        f"{API}/auth/reset-password",
        json={"token": token, "new_password": "BrandNew99"},
    )
    assert first.status_code == 200

    # Reusar el mismo token debe fallar (ya se limpió en BD).
    second = await client.post(
        f"{API}/auth/reset-password",
        json={"token": token, "new_password": "Another99"},
    )
    assert second.status_code == 401


async def test_reset_with_garbage_token(client):
    r = await client.post(
        f"{API}/auth/reset-password",
        json={"token": "not-a-jwt", "new_password": "Whatever99"},
    )
    assert r.status_code == 401


async def test_forgot_password_unknown_email_is_silent(client):
    # No revela si el email existe: siempre 202.
    r = await client.post(
        f"{API}/auth/forgot-password",
        json={"email": "ghost@example.com"},
    )
    assert r.status_code == 202
