"""
Tests del reenvío del correo de verificación.

Por qué existe este endpoint: el envío del correo en el registro es
best-effort (la excepción se ignora para que un SMTP caído no tumbe el
alta). Sin un reenvío, un fallo transitorio dejaba la cuenta sin
verificar y sin salida: volver a registrarse devuelve 409 y todos los
endpoints protegidos exigen email verificado.
"""

import pytest
from sqlalchemy import select

from app.models.user import User
from tests.conftest import API


@pytest.fixture
def enviados(monkeypatch):
    """Captura las llamadas al envío de correo de verificación."""
    llamadas: list[dict] = []

    async def _spy(email, full_name, token):
        llamadas.append(
            {"email": email, "full_name": full_name, "token": token}
        )

    monkeypatch.setattr(
        "app.services.auth.send_verification_email", _spy
    )
    return llamadas


async def _registrar(client, email, password="Tormenta7Azul"):
    r = await client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
        },
    )
    assert r.status_code == 201, r.text


@pytest.mark.asyncio
async def test_reenvia_a_usuario_sin_verificar(client, db, enviados):
    await _registrar(client, "pendiente@example.com")
    enviados.clear()  # descarta el envío del registro

    r = await client.post(
        f"{API}/auth/resend-verification",
        json={"email": "pendiente@example.com"},
    )

    assert r.status_code == 202
    assert len(enviados) == 1
    assert enviados[0]["email"] == "pendiente@example.com"
    assert enviados[0]["token"]


@pytest.mark.asyncio
async def test_reusa_el_token_existente(client, db, enviados):
    """
    El enlace del correo original debe seguir sirviendo: generar un
    token nuevo dejaría al usuario con dos correos y uno muerto.
    """
    await _registrar(client, "pendiente2@example.com")
    user = (
        await db.execute(
            select(User).where(User.email == "pendiente2@example.com")
        )
    ).scalar_one()
    token_original = user.email_verification_token
    enviados.clear()

    await client.post(
        f"{API}/auth/resend-verification",
        json={"email": "pendiente2@example.com"},
    )

    assert enviados[0]["token"] == token_original


@pytest.mark.asyncio
async def test_el_token_reenviado_verifica_de_verdad(
    client, db, enviados
):
    """El flujo completo: reenviar y verificar con ese token."""
    await _registrar(client, "pendiente3@example.com")
    enviados.clear()

    await client.post(
        f"{API}/auth/resend-verification",
        json={"email": "pendiente3@example.com"},
    )
    token = enviados[0]["token"]

    r = await client.get(f"{API}/auth/verify-email?token={token}")
    assert r.status_code == 200

    await db.commit()
    user = (
        await db.execute(
            select(User).where(User.email == "pendiente3@example.com")
        )
    ).scalar_one()
    await db.refresh(user)
    assert user.is_verified is True


@pytest.mark.asyncio
async def test_no_reenvia_a_usuario_ya_verificado(
    client, db, enviados
):
    """Un correo de verificación a quien ya verificó es ruido inútil."""
    await _registrar(client, "yaesta@example.com")
    user = (
        await db.execute(
            select(User).where(User.email == "yaesta@example.com")
        )
    ).scalar_one()
    user.is_verified = True
    await db.commit()
    enviados.clear()

    r = await client.post(
        f"{API}/auth/resend-verification",
        json={"email": "yaesta@example.com"},
    )

    assert r.status_code == 202  # misma respuesta, sin revelar nada
    assert enviados == []


@pytest.mark.asyncio
async def test_email_desconocido_no_revela_nada(client, db, enviados):
    """202 silencioso: el endpoint no sirve para enumerar cuentas."""
    enviados.clear()

    r = await client.post(
        f"{API}/auth/resend-verification",
        json={"email": "nadie-aqui@example.com"},
    )

    assert r.status_code == 202
    assert enviados == []


@pytest.mark.asyncio
async def test_email_invalido_da_422(client):
    r = await client.post(
        f"{API}/auth/resend-verification", json={"email": "no-es-email"}
    )
    assert r.status_code == 422
