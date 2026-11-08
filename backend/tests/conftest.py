"""
Configuración de tests del backend.

Estrategia:
- Base de datos dedicada `sajjad_test` (Postgres real) — los modelos
  usan tipos del dialecto Postgres (UUID, JSON), así que no se puede
  testear contra SQLite sin reescribirlos.
- Engine y esquema por test (create_all/drop_all con NullPool): da
  aislamiento total y evita problemas de event-loop entre tests con
  asyncpg (cada test corre en su propio loop de pytest-asyncio).
- Se sobreescribe la dependencia `get_db` para que la app use el
  engine de test, sobre un AsyncClient encima de la app ASGI.
- Se mockean Celery (`run_scan.delay`), el envío de email y la
  verificación DNS para correr sin red ni broker.
"""

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# El Postgres dockerizado está expuesto en localhost:5432 (sajjad:sajjad).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://sajjad:sajjad@localhost:5432/sajjad_test",
)

# Importar después de fijar TEST_DATABASE_URL, de ahí los E402.
import app.models  # noqa: E402,F401  (registra todos los modelos)
from app.database import (  # noqa: E402
    Base,
    get_db,
    get_sessionmaker,
)
from app.main import app as fastapi_app  # noqa: E402

API = "/api/v1"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        TEST_DATABASE_URL, echo=False, poolclass=NullPool
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def sessionmaker_(engine):
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db(sessionmaker_) -> AsyncGenerator[AsyncSession, None]:
    async with sessionmaker_() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
def _disable_rate_limit():
    """
    Apaga el rate limiting durante los tests.

    La suite llama a /auth/login y /auth/register decenas de veces
    seguidas desde la misma "IP": con los límites activos los tests
    se estorbarían entre sí. Los límites tienen su propio test, que
    los vuelve a encender explícitamente.
    """
    from app.core.ratelimit import limiter

    limiter.enabled = False
    yield
    limiter.enabled = False


@pytest_asyncio.fixture(autouse=True)
def _patch_externals(monkeypatch):
    """Mockea efectos externos: email, Celery, verificación DNS."""

    async def _noop_email(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.auth.send_verification_email", _noop_email
    )
    monkeypatch.setattr(
        "app.services.email.send_password_reset_email",
        _noop_email,
        raising=False,
    )

    class _FakeTask:
        id = "test-task-id"

    def _fake_delay(*args, **kwargs):
        return _FakeTask()

    monkeypatch.setattr(
        "app.routers.scans.run_scan.delay", _fake_delay
    )

    async def _ok_verify(fqdn, token):
        return True

    monkeypatch.setattr(
        "app.routers.domains.verify_domain_ownership", _ok_verify
    )


@pytest_asyncio.fixture
def billing_on(monkeypatch):
    """
    Enciende la pasarela de pagos para un test.

    `get_settings` está cacheada con lru_cache y todos los módulos
    comparten ese mismo objeto función, así que basta con fijar la
    variable de entorno y limpiar la caché: la siguiente llamada
    reconstruye Settings desde el entorno en todo el proceso.
    """
    from app.config import get_settings

    monkeypatch.setenv("BILLING_ENABLED", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("BILLING_ENABLED", raising=False)
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def client(sessionmaker_):
    from httpx import ASGITransport, AsyncClient

    async def _override_get_db():
        async with sessionmaker_() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    # El stream SSE abre sus propias sesiones cortas a través de esta
    # factoría; sin sobreescribirla iría al Postgres de desarrollo.
    fastapi_app.dependency_overrides[get_sessionmaker] = (
        lambda: sessionmaker_
    )
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


# ── Helpers de alto nivel ───────────────────────────────────


async def register_and_verify(
    client, db, email="user@example.com", password="Tormenta7Azul",
    plan="free",
):
    """Registra un usuario, lo marca verificado, fija su plan y
    devuelve (user, tokens)."""
    from sqlalchemy import select

    from app.models.subscription import Subscription
    from app.models.user import User

    r = await client.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
        },
    )
    assert r.status_code == 201, r.text

    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one()
    user.is_verified = True
    sub = (
        await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
    ).scalar_one()
    sub.plan = plan
    await db.commit()

    login = await client.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return user, login.json()


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
