"""
Tests del sobre de error y de la pila de middleware.

Regresión: un 500 salía SIN cabeceras CORS, porque el handler de
`Exception` de Starlette vive en ServerErrorMiddleware, por fuera del
CORSMiddleware. En el navegador eso aparece como un error de CORS y el
frontend no puede leer el cuerpo: el `{"error": ..., "message": ...}`
que `lib/errors.ts` traduce nunca llegaba, y en producción un 500
parecía un problema de configuración de CORS.
"""

import pytest

from tests.conftest import API

ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.mark.asyncio
async def test_error_interno_lleva_cabeceras_cors(client, monkeypatch):
    """Un 500 tiene que ser legible por el navegador."""

    async def _explota(*args, **kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(
        "app.routers.auth.auth_service.login_user", _explota
    )

    r = await client.post(
        f"{API}/auth/login",
        json={"email": "quien@example.com", "password": "Tormenta7Azul"},
        headers=ORIGIN,
    )

    assert r.status_code == 500
    assert r.headers.get("access-control-allow-origin") == (
        "http://localhost:3000"
    )
    assert r.json()["error"] == "InternalServerError"


@pytest.mark.asyncio
async def test_error_interno_no_filtra_detalles(client, monkeypatch):
    """El mensaje de la excepción no debe viajar al cliente."""

    async def _explota(*args, **kwargs):
        raise RuntimeError("DATABASE_URL=postgres://user:secreto@host")

    monkeypatch.setattr(
        "app.routers.auth.auth_service.login_user", _explota
    )

    r = await client.post(
        f"{API}/auth/login",
        json={"email": "quien@example.com", "password": "Tormenta7Azul"},
        headers=ORIGIN,
    )

    assert "secreto" not in r.text
    assert "postgres" not in r.text


@pytest.mark.asyncio
async def test_error_de_negocio_lleva_cabeceras_cors(client):
    """Los errores propios (aquí 401) ya pasaban por CORS: no regresar."""
    r = await client.post(
        f"{API}/auth/login",
        json={"email": "nadie@example.com", "password": "Tormenta7Azul"},
        headers=ORIGIN,
    )

    assert r.status_code == 401
    assert r.headers.get("access-control-allow-origin") == (
        "http://localhost:3000"
    )
    assert r.json()["error"] == "Unauthorized"


@pytest.mark.asyncio
async def test_respuesta_trae_request_id(client):
    """Correlación de logs: cada respuesta expone su X-Request-ID."""
    r = await client.get("/health", headers=ORIGIN)
    assert r.headers.get("X-Request-ID")
    assert r.headers.get("X-Response-Time")


@pytest.mark.asyncio
async def test_request_id_del_cliente_se_respeta(client):
    """Si el cliente manda uno, se reusa para poder rastrear la petición."""
    r = await client.get(
        "/health", headers={**ORIGIN, "X-Request-ID": "rastro-123"}
    )
    assert r.headers["X-Request-ID"] == "rastro-123"
