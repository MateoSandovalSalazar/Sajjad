"""Tests de gestión de dominios y enforcement de límites de plan."""

import pytest

from tests.conftest import API, auth_headers, register_and_verify

pytestmark = pytest.mark.asyncio


async def test_add_and_list_domain(client, db):
    _, tokens = await register_and_verify(client, db)
    h = auth_headers(tokens)

    r = await client.post(
        f"{API}/domains",
        json={"fqdn": "example.com", "authorized": True},
        headers=h,
    )
    assert r.status_code == 201, r.text
    domain = r.json()
    assert domain["fqdn"] == "example.com"
    assert domain["is_verified"] is False
    assert domain["verification_token"].startswith("sajjad-verify-")

    lst = await client.get(f"{API}/domains", headers=h)
    assert lst.status_code == 200
    assert len(lst.json()) == 1


async def test_get_domain_by_id(client, db):
    _, tokens = await register_and_verify(client, db)
    h = auth_headers(tokens)
    created = (
        await client.post(
            f"{API}/domains",
            json={"fqdn": "example.com", "authorized": True},
            headers=h,
        )
    ).json()

    r = await client.get(
        f"{API}/domains/{created['id']}", headers=h
    )
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_free_plan_domain_limit(client, db):
    _, tokens = await register_and_verify(client, db)
    h = auth_headers(tokens)

    first = await client.post(
        f"{API}/domains",
        json={"fqdn": "example.com", "authorized": True},
        headers=h,
    )
    assert first.status_code == 201

    # Plan free = 1 dominio → el segundo debe dar 402.
    second = await client.post(
        f"{API}/domains",
        json={"fqdn": "other.com", "authorized": True},
        headers=h,
    )
    assert second.status_code == 402


async def test_professional_plan_allows_more_domains(client, db):
    _, tokens = await register_and_verify(
        client, db, email="pro@example.com", plan="professional"
    )
    h = auth_headers(tokens)

    for fqdn in ("a.com", "b.com", "c.com"):
        r = await client.post(
            f"{API}/domains",
            json={"fqdn": fqdn, "authorized": True},
            headers=h,
        )
        assert r.status_code == 201, r.text


async def test_duplicate_domain_conflict(client, db):
    _, tokens = await register_and_verify(
        client, db, plan="professional"
    )
    h = auth_headers(tokens)
    await client.post(
        f"{API}/domains",
        json={"fqdn": "example.com", "authorized": True},
        headers=h,
    )
    dup = await client.post(
        f"{API}/domains",
        json={"fqdn": "example.com", "authorized": True},
        headers=h,
    )
    assert dup.status_code == 409


async def test_cannot_access_other_users_domain(client, db):
    _, t1 = await register_and_verify(
        client, db, email="owner@example.com"
    )
    created = (
        await client.post(
            f"{API}/domains",
            json={"fqdn": "example.com", "authorized": True},
            headers=auth_headers(t1),
        )
    ).json()

    _, t2 = await register_and_verify(
        client, db, email="intruder@example.com"
    )
    r = await client.get(
        f"{API}/domains/{created['id']}",
        headers=auth_headers(t2),
    )
    # 404 y no 403 a propósito: un 403 confirmaría que ese id existe y
    # dejaría enumerar los dominios de otras cuentas.
    assert r.status_code == 404


async def test_unverified_user_cannot_add_domain(client, db):
    # Registrar SIN verificar.
    await client.post(
        f"{API}/auth/register",
        json={
            "email": "unverified@example.com",
            "password": "Tormenta7Azul",
            "full_name": "U",
        },
    )
    login = await client.post(
        f"{API}/auth/login",
        json={
            "email": "unverified@example.com",
            "password": "Tormenta7Azul",
        },
    )
    r = await client.post(
        f"{API}/domains",
        json={"fqdn": "example.com", "authorized": True},
        headers=auth_headers(login.json()),
    )
    assert r.status_code == 403


async def test_verify_instructions_endpoint(client, db):
    """Regresión: el endpoint construía el schema con campos
    equivocados y devolvía 500."""
    _, tokens = await register_and_verify(client, db)
    h = auth_headers(tokens)
    created = (
        await client.post(
            f"{API}/domains",
            json={"fqdn": "example.com", "authorized": True},
            headers=h,
        )
    ).json()

    r = await client.get(
        f"{API}/domains/{created['id']}/instructions", headers=h
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fqdn"] == "example.com"
    assert body["dns_record_type"] == "TXT"
    assert body["dns_record_value"] == created["verification_token"]


async def test_trigger_verify_marks_domain_verified(client, db):
    _, tokens = await register_and_verify(client, db)
    h = auth_headers(tokens)
    created = (
        await client.post(
            f"{API}/domains",
            json={"fqdn": "example.com", "authorized": True},
            headers=h,
        )
    ).json()

    # verify_domain_ownership está mockeado a OK en conftest.
    r = await client.post(
        f"{API}/domains/{created['id']}/verify", headers=h
    )
    assert r.status_code == 200
    assert r.json()["is_verified"] is True


async def test_delete_domain(client, db):
    _, tokens = await register_and_verify(client, db)
    h = auth_headers(tokens)
    created = (
        await client.post(
            f"{API}/domains",
            json={"fqdn": "example.com", "authorized": True},
            headers=h,
        )
    ).json()

    r = await client.delete(
        f"{API}/domains/{created['id']}", headers=h
    )
    assert r.status_code == 204

    lst = await client.get(f"{API}/domains", headers=h)
    assert lst.json() == []


# ── Autorización de escaneo ─────────────────────────────────


async def test_domain_requires_authorization_declaration(client, db):
    """
    Sin la declaración de propiedad no se da de alta el dominio.

    Sajjad escanea infraestructura ajena: el consentimiento explícito
    es la base legal de cada escaneo, no un detalle de formulario.
    """
    _, tokens = await register_and_verify(client, db)
    h = auth_headers(tokens)

    sin_flag = await client.post(
        f"{API}/domains", json={"fqdn": "example.com"}, headers=h
    )
    assert sin_flag.status_code == 422

    explicito_false = await client.post(
        f"{API}/domains",
        json={"fqdn": "example.com", "authorized": False},
        headers=h,
    )
    assert explicito_false.status_code == 422

    # Y no se creó nada.
    lst = await client.get(f"{API}/domains", headers=h)
    assert lst.json() == []


async def test_authorization_is_recorded_with_evidence(client, db):
    """
    La declaración queda con fecha, IP y user-agent: un checkbox sin
    rastro no prueba nada si algún día hay que defenderlo.
    """
    from sqlalchemy import select

    from app.models.domain import Domain

    _, tokens = await register_and_verify(client, db)
    r = await client.post(
        f"{API}/domains",
        json={"fqdn": "example.com", "authorized": True},
        headers={**auth_headers(tokens), "User-Agent": "Navegador/1.0"},
    )
    assert r.status_code == 201

    domain = (
        await db.execute(
            select(Domain).where(Domain.fqdn == "example.com")
        )
    ).scalar_one()

    assert domain.authorized_at is not None
    assert domain.authorized_user_agent == "Navegador/1.0"
