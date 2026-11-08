"""Tests de lanzamiento de escaneos y límites mensuales."""

from datetime import UTC

import pytest
from sqlalchemy import select

from app.models.domain import Domain
from app.models.subscription import Subscription
from tests.conftest import API, auth_headers, register_and_verify

pytestmark = pytest.mark.asyncio


async def _make_verified_domain(client, db, tokens, fqdn="example.com"):
    h = auth_headers(tokens)
    created = (
        await client.post(
            f"{API}/domains",
            json={"fqdn": fqdn, "authorized": True},
            headers=h,
        )
    ).json()
    # Marcar el dominio como verificado en la BD.
    res = await db.execute(
        select(Domain).where(Domain.id == created["id"])
    )
    domain = res.scalar_one()
    from datetime import datetime

    domain.verified_at = datetime.now(UTC)
    await db.commit()
    return created


async def test_launch_scan_on_unverified_domain_fails(client, db):
    _, tokens = await register_and_verify(
        client, db, plan="starter"
    )
    h = auth_headers(tokens)
    created = (
        await client.post(
            f"{API}/domains",
            json={"fqdn": "example.com", "authorized": True},
            headers=h,
        )
    ).json()

    r = await client.post(
        f"{API}/scans",
        json={"domain_id": created["id"]},
        headers=h,
    )
    assert r.status_code == 400  # DomainNotVerified


async def test_launch_scan_success(client, db):
    _, tokens = await register_and_verify(
        client, db, plan="starter"
    )
    created = await _make_verified_domain(client, db, tokens)

    r = await client.post(
        f"{API}/scans",
        json={"domain_id": created["id"]},
        headers=auth_headers(tokens),
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["domain_id"] == created["id"]


async def test_concurrent_scan_rejected(client, db):
    _, tokens = await register_and_verify(
        client, db, plan="starter"
    )
    created = await _make_verified_domain(client, db, tokens)
    h = auth_headers(tokens)

    first = await client.post(
        f"{API}/scans", json={"domain_id": created["id"]}, headers=h
    )
    assert first.status_code == 202

    second = await client.post(
        f"{API}/scans", json={"domain_id": created["id"]}, headers=h
    )
    assert second.status_code == 409  # ScanAlreadyRunning


async def test_monthly_scan_limit_enforced(client, db):
    user, tokens = await register_and_verify(
        client, db, plan="starter"
    )
    created = await _make_verified_domain(client, db, tokens)

    # Forzar el contador al tope del plan starter (4) en el mes actual.
    from datetime import datetime

    sub = (
        await db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id
            )
        )
    ).scalar_one()
    sub.scans_this_month = 4
    sub.scans_reset_at = datetime.now(UTC)
    await db.commit()

    r = await client.post(
        f"{API}/scans",
        json={"domain_id": created["id"]},
        headers=auth_headers(tokens),
    )
    assert r.status_code == 402  # PlanLimitExceeded


async def test_lazy_monthly_reset_allows_scan(client, db):
    """Si el último reset fue el mes pasado, el contador se reinicia
    de forma perezosa al lanzar y el escaneo procede."""
    user, tokens = await register_and_verify(
        client, db, plan="starter"
    )
    created = await _make_verified_domain(client, db, tokens)

    from datetime import datetime

    sub = (
        await db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id
            )
        )
    ).scalar_one()
    sub.scans_this_month = 4  # tope alcanzado...
    # ...pero el reset fue hace mucho (mes/año anterior).
    sub.scans_reset_at = datetime(2020, 1, 1, tzinfo=UTC)
    await db.commit()

    r = await client.post(
        f"{API}/scans",
        json={"domain_id": created["id"]},
        headers=auth_headers(tokens),
    )
    assert r.status_code == 202, r.text

    await db.refresh(sub)
    assert sub.scans_this_month == 0
    assert sub.scans_reset_at.year >= 2026


async def test_get_scan_status(client, db):
    _, tokens = await register_and_verify(
        client, db, plan="starter"
    )
    created = await _make_verified_domain(client, db, tokens)
    h = auth_headers(tokens)
    scan = (
        await client.post(
            f"{API}/scans", json={"domain_id": created["id"]}, headers=h
        )
    ).json()

    r = await client.get(f"{API}/scans/{scan['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["id"] == scan["id"]


async def test_findings_locked_on_free_plan(client, db):
    _, tokens = await register_and_verify(client, db, plan="free")
    # En free no podemos crear escaneos verificados fácilmente sin
    # dominio verificado; verificamos el gate de findings con un id
    # cualquiera: debe dar 402 antes de tocar la BD.
    import uuid

    r = await client.get(
        f"{API}/scans/{uuid.uuid4()}/findings",
        headers=auth_headers(tokens),
    )
    assert r.status_code == 402
