"""
Tests del stream SSE de progreso de escaneo.

Lo que de verdad importa aquí no es el formato de los eventos, sino
que el stream TERMINE siempre: mientras está abierto consume un slot
de conexión, y un escaneo que se queda colgado (worker caído) dejaba
el stream girando para siempre. Con pool_size=10, diez clientes
pegados a escaneos colgados dejaban la API entera sin conexiones.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.domain import Domain
from app.models.scan import Scan, ScanStatus
from tests.conftest import API, register_and_verify


async def _verified_domain_and_scan(client, db, email):
    """Devuelve (headers, scan_id) con un dominio ya verificado."""
    _user, tokens = await register_and_verify(
        client, db, email=email, plan="starter"
    )
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = await client.post(
        f"{API}/domains",
        json={"fqdn": "ejemplo.com", "authorized": True},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    domain_id = r.json()["id"]

    domain = (
        await db.execute(select(Domain).where(Domain.id == domain_id))
    ).scalar_one()
    domain.verified_at = datetime.now(timezone.utc)
    await db.commit()

    r = await client.post(
        f"{API}/scans", json={"domain_id": domain_id}, headers=headers
    )
    assert r.status_code == 202, r.text
    return headers, r.json()["id"]


@pytest.mark.asyncio
async def test_stream_termina_en_scan_completado(client, db):
    """Un escaneo ya terminal emite su evento y cierra el stream."""
    headers, scan_id = await _verified_domain_and_scan(
        client, db, "stream1@example.com"
    )

    scan = (
        await db.execute(select(Scan).where(Scan.id == scan_id))
    ).scalar_one()
    scan.status = ScanStatus.COMPLETED
    scan.risk_score = 42
    scan.risk_level = "medium"
    scan.completed_at = datetime.now(timezone.utc)
    await db.commit()

    r = await client.get(f"{API}/scans/{scan_id}/stream", headers=headers)

    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert '"status": "completed"' in r.text
    assert '"risk_score": 42' in r.text


@pytest.mark.asyncio
async def test_stream_corta_por_tope_de_tiempo(client, db, monkeypatch):
    """
    Un escaneo que nunca termina no deja el stream abierto para
    siempre: al vencer el tope se emite un evento `timeout` y se
    cierra, liberando la conexión.
    """
    from app.routers import scans

    monkeypatch.setattr(scans, "_STREAM_MAX_SECONDS", 0)
    monkeypatch.setattr(scans, "_STREAM_POLL_SECONDS", 0)

    headers, scan_id = await _verified_domain_and_scan(
        client, db, "stream2@example.com"
    )

    # El scan se queda en PENDING: sin tope, esto no retornaría nunca.
    r = await client.get(f"{API}/scans/{scan_id}/stream", headers=headers)

    assert r.status_code == 200
    assert '"status": "pending"' in r.text
    assert "event: timeout" in r.text


@pytest.mark.asyncio
async def test_stream_ajeno_da_404(client, db):
    """El stream de otro usuario no se abre."""
    headers, scan_id = await _verified_domain_and_scan(
        client, db, "stream3@example.com"
    )
    _other, other_tokens = await register_and_verify(
        client, db, email="intruso@example.com", plan="starter"
    )

    r = await client.get(
        f"{API}/scans/{scan_id}/stream",
        headers={"Authorization": f"Bearer {other_tokens['access_token']}"},
    )
    assert r.status_code == 404
