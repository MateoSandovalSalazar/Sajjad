"""Tests del flujo de autenticación."""

import pytest
from sqlalchemy import select

from app.models.user import User
from tests.conftest import API, auth_headers

pytestmark = pytest.mark.asyncio


VALID = {
    "email": "alice@example.com",
    "password": "Tormenta7Azul",
    "full_name": "Alice",
}


async def test_register_creates_user_and_subscription(client, db):
    r = await client.post(f"{API}/auth/register", json=VALID)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == VALID["email"]
    assert body["is_verified"] is False

    # Se crea una suscripción free automática.
    from app.models.subscription import Subscription

    res = await db.execute(
        select(User).where(User.email == VALID["email"])
    )
    user = res.scalar_one()
    sub = (
        await db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id
            )
        )
    ).scalar_one()
    assert sub.plan == "free"


async def test_register_duplicate_email_conflict(client):
    await client.post(f"{API}/auth/register", json=VALID)
    r = await client.post(f"{API}/auth/register", json=VALID)
    assert r.status_code == 409


async def test_register_weak_password_rejected(client):
    r = await client.post(
        f"{API}/auth/register",
        json={**VALID, "password": "alllowercase"},
    )
    assert r.status_code == 422


async def test_login_wrong_password(client):
    await client.post(f"{API}/auth/register", json=VALID)
    r = await client.post(
        f"{API}/auth/login",
        json={"email": VALID["email"], "password": "Wrong0000"},
    )
    assert r.status_code == 401


async def test_login_unknown_email(client):
    r = await client.post(
        f"{API}/auth/login",
        json={"email": "ghost@example.com", "password": "Tormenta7Azul"},
    )
    assert r.status_code == 401


async def test_login_returns_tokens_unverified(client):
    await client.post(f"{API}/auth/register", json=VALID)
    r = await client.post(
        f"{API}/auth/login",
        json={"email": VALID["email"], "password": VALID["password"]},
    )
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["is_verified"] is False


async def test_verify_email_flow(client, db):
    await client.post(f"{API}/auth/register", json=VALID)
    res = await db.execute(
        select(User).where(User.email == VALID["email"])
    )
    user = res.scalar_one()
    token = user.email_verification_token
    assert token

    r = await client.get(
        f"{API}/auth/verify-email", params={"token": token}
    )
    assert r.status_code == 200

    await db.refresh(user)
    assert user.is_verified is True
    assert user.email_verification_token is None


async def test_verify_email_bad_token(client):
    r = await client.get(
        f"{API}/auth/verify-email", params={"token": "nope"}
    )
    assert r.status_code == 404


async def test_refresh_token(client):
    await client.post(f"{API}/auth/register", json=VALID)
    login = await client.post(
        f"{API}/auth/login",
        json={"email": VALID["email"], "password": VALID["password"]},
    )
    refresh = login.json()["refresh_token"]
    r = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": refresh}
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_refresh_rejects_access_token(client):
    await client.post(f"{API}/auth/register", json=VALID)
    login = await client.post(
        f"{API}/auth/login",
        json={"email": VALID["email"], "password": VALID["password"]},
    )
    access = login.json()["access_token"]
    # Pasar un access token donde se espera un refresh debe fallar.
    r = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": access}
    )
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 401


async def test_me_with_token(client):
    await client.post(f"{API}/auth/register", json=VALID)
    login = await client.post(
        f"{API}/auth/login",
        json={"email": VALID["email"], "password": VALID["password"]},
    )
    r = await client.get(
        f"{API}/auth/me", headers=auth_headers(login.json())
    )
    assert r.status_code == 200
    assert r.json()["email"] == VALID["email"]
