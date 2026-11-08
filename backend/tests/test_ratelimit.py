"""
Tests del rate limiting.

El resto de la suite lo tiene desactivado (llama a los mismos
endpoints decenas de veces), así que estos tests lo vuelven a
encender a propósito y usan un almacenamiento en memoria para no
depender de Redis ni ensuciar contadores entre ejecuciones.
"""

import pytest

from tests.conftest import API

pytestmark = pytest.mark.asyncio


@pytest.fixture
def rate_limit_on():
    """
    Enciende el limiter con almacenamiento en memoria y lo deja
    limpio al terminar.
    """
    from limits.storage import MemoryStorage
    from limits.strategies import FixedWindowRateLimiter

    from app.core.ratelimit import limiter

    original_storage = limiter._storage
    original_limiter = limiter._limiter

    storage = MemoryStorage()
    limiter._storage = storage
    limiter._limiter = FixedWindowRateLimiter(storage)
    limiter.enabled = True

    yield

    limiter.enabled = False
    limiter._storage = original_storage
    limiter._limiter = original_limiter


async def test_login_brute_force_is_blocked(client, rate_limit_on):
    """
    Adivinar contraseñas tiene que toparse con un muro.

    Sin esto, /auth/login acepta intentos ilimitados: un diccionario
    contra una cuenta conocida es cuestión de tiempo.
    """
    body = {"email": "victima@example.com", "password": "intento"}

    codes = []
    for _ in range(15):
        r = await client.post(f"{API}/auth/login", json=body)
        codes.append(r.status_code)

    assert 429 in codes, (
        "El login aceptó 15 intentos seguidos sin cortar: "
        "el rate limit no está aplicado."
    )

    # Y el 429 llega en el sobre de error estándar de la API.
    last = await client.post(f"{API}/auth/login", json=body)
    assert last.status_code == 429
    assert last.json()["error"] == "RateLimitExceeded"


async def test_register_flood_is_blocked(client, rate_limit_on):
    """Frena el alta masiva de cuentas para encadenar pruebas."""
    codes = []
    for i in range(8):
        r = await client.post(
            f"{API}/auth/register",
            json={
                "email": f"masivo{i}@example.com",
                "password": "Tormenta7Azul",
                "full_name": "Masivo",
            },
        )
        codes.append(r.status_code)

    assert 429 in codes


async def test_forgot_password_flood_is_blocked(client, rate_limit_on):
    """
    Cada petición manda un correo a una dirección que elige quien
    llama: sin límite es un arma de bombardeo contra terceros.
    """
    codes = []
    for _ in range(6):
        r = await client.post(
            f"{API}/auth/forgot-password",
            json={"email": "alguien@example.com"},
        )
        codes.append(r.status_code)

    assert 429 in codes


async def test_limits_are_off_for_the_rest_of_the_suite(client):
    """
    Guardarraíl del propio andamiaje: sin `rate_limit_on`, el limiter
    debe estar apagado. Si esto falla, otros tests fallarán de forma
    intermitente y confusa.
    """
    from app.core.ratelimit import limiter

    assert limiter.enabled is False
