"""
Tests del endurecimiento de autenticación.

Cubren tres defensas concretas: no filtrar qué emails existen,
invalidar las sesiones al cambiar la contraseña, y no aceptar
contraseñas de diccionario.
"""

import time

import pytest

from app.core.passwords import validate_password
from tests.conftest import API, auth_headers, register_and_verify

# Sin `pytestmark` a propósito: el proyecto usa asyncio_mode="auto",
# que detecta las corrutinas solo. Marcar el módulo entero como
# asyncio haría que los tests síncronos de la política de contraseñas
# emitan avisos.


# ── Enumeración de usuarios ──────────────────────────────────


async def test_login_same_message_for_unknown_and_wrong_password(
    client, db
):
    """El mensaje no debe revelar si el email existe."""
    await register_and_verify(client, db, email="existe@example.com")

    inexistente = await client.post(
        f"{API}/auth/login",
        json={"email": "nadie@example.com", "password": "Tormenta7Azul"},
    )
    mal_pass = await client.post(
        f"{API}/auth/login",
        json={"email": "existe@example.com", "password": "Otra1234"},
    )

    assert inexistente.status_code == mal_pass.status_code == 401
    assert inexistente.json()["message"] == mal_pass.json()["message"]


async def test_login_timing_does_not_leak_user_existence(client, db):
    """
    Los dos caminos deben costar lo mismo.

    Si sólo se hiciera bcrypt cuando el usuario existe, la rama
    "no existe" respondería ~100 ms antes y bastaría cronometrar
    para enumerar la base de usuarios.
    """
    await register_and_verify(client, db, email="existe@example.com")

    def _elapsed(coro_factory):
        async def _run():
            start = time.perf_counter()
            await coro_factory()
            return time.perf_counter() - start
        return _run()

    t_existe = await _elapsed(lambda: client.post(
        f"{API}/auth/login",
        json={"email": "existe@example.com", "password": "Mala1234"},
    ))
    t_no_existe = await _elapsed(lambda: client.post(
        f"{API}/auth/login",
        json={"email": "nadie@example.com", "password": "Mala1234"},
    ))

    # bcrypt domina ambos caminos: la diferencia debe ser una
    # fracción del coste total, no un orden de magnitud.
    assert min(t_existe, t_no_existe) > 0
    ratio = max(t_existe, t_no_existe) / min(t_existe, t_no_existe)
    assert ratio < 5, (
        f"Diferencia de tiempo sospechosa: existe={t_existe:.3f}s "
        f"no_existe={t_no_existe:.3f}s (ratio {ratio:.1f}x)"
    )


async def test_forgot_password_does_not_reveal_unknown_email(client):
    r = await client.post(
        f"{API}/auth/forgot-password",
        json={"email": "nadie-en-absoluto@example.com"},
    )
    assert r.status_code == 202


# ── Invalidación de sesiones ─────────────────────────────────


async def test_password_change_invalidates_existing_tokens(client, db):
    """
    Cambiar la contraseña tiene que echar a quien tuviera la sesión.

    Es el caso de uso central: si te roban la cuenta, cambiar la
    contraseña debe expulsar al atacante, no dejarle 30 días de
    refresh token válido.
    """
    _, tokens = await register_and_verify(client, db)
    viejo = auth_headers(tokens)

    # El token viejo funciona ahora.
    antes = await client.get(f"{API}/users/me", headers=viejo)
    assert antes.status_code == 200

    r = await client.post(
        f"{API}/users/me/password",
        json={
            "current_password": "Tormenta7Azul",
            "new_password": "NuevaClave456",
        },
        headers=viejo,
    )
    assert r.status_code == 200

    # Y deja de funcionar inmediatamente después.
    despues = await client.get(f"{API}/users/me", headers=viejo)
    assert despues.status_code == 401

    # El refresh token viejo tampoco sirve.
    refresh = await client.post(
        f"{API}/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 401


async def test_password_reset_invalidates_existing_tokens(client, db):
    """Lo mismo por la vía de "olvidé mi contraseña"."""
    from sqlalchemy import select

    from app.models.user import User

    _, tokens = await register_and_verify(client, db)
    viejo = auth_headers(tokens)

    await client.post(
        f"{API}/auth/forgot-password",
        json={"email": "user@example.com"},
    )
    res = await db.execute(
        select(User).where(User.email == "user@example.com")
    )
    user = res.scalar_one()
    await db.refresh(user)
    reset_token = user.password_reset_token
    assert reset_token

    r = await client.post(
        f"{API}/auth/reset-password",
        json={"token": reset_token, "new_password": "OtraClave789"},
    )
    assert r.status_code == 200

    assert (
        await client.get(f"{API}/users/me", headers=viejo)
    ).status_code == 401


async def test_new_session_works_after_password_change(client, db):
    """El usuario legítimo puede volver a entrar sin fricción."""
    await register_and_verify(client, db)
    login = await client.post(
        f"{API}/auth/login",
        json={"email": "user@example.com", "password": "Tormenta7Azul"},
    )
    await client.post(
        f"{API}/users/me/password",
        json={
            "current_password": "Tormenta7Azul",
            "new_password": "NuevaClave456",
        },
        headers=auth_headers(login.json()),
    )

    nuevo = await client.post(
        f"{API}/auth/login",
        json={"email": "user@example.com", "password": "NuevaClave456"},
    )
    assert nuevo.status_code == 200
    me = await client.get(
        f"{API}/users/me", headers=auth_headers(nuevo.json())
    )
    assert me.status_code == 200


# ── Política de contraseñas ──────────────────────────────────


@pytest.mark.parametrize(
    "mala",
    [
        "Password1",     # la más común que pasaba el validador viejo
        "Passw0rd123",   # variante con leet
        "Qwerty123",
        "Welcome123",
        "Aaaaaaa1",      # sólo 3 caracteres distintos
        "Sajjad123",     # el nombre del propio producto
    ],
)
def test_weak_passwords_rejected(mala):
    with pytest.raises(ValueError):
        validate_password(mala)


@pytest.mark.parametrize(
    "buena",
    ["Tormenta7Azul", "k9Lm2pQrs", "MiPerroCome4Veces"],
)
def test_reasonable_passwords_accepted(buena):
    assert validate_password(buena) == buena


async def test_register_rejects_common_password(client):
    r = await client.post(
        f"{API}/auth/register",
        json={
            "email": "debil@example.com",
            "password": "Password1",
            "full_name": "Débil",
        },
    )
    assert r.status_code == 422


async def test_change_password_enforces_policy(client, db):
    """
    Este endpoint no validaba nada: se podía dejar la cuenta con la
    contraseña "a".
    """
    _, tokens = await register_and_verify(client, db)
    r = await client.post(
        f"{API}/users/me/password",
        json={"current_password": "Tormenta7Azul", "new_password": "a"},
        headers=auth_headers(tokens),
    )
    assert r.status_code == 422
