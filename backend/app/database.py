from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    # echo=False a propósito. Con echo=True, SQLAlchemy instala SU
    # PROPIO handler en el logger `sqlalchemy.engine`, que además
    # propaga al root —donde configure_logging() ya puso el nuestro—,
    # así que cada sentencia SQL se imprimía DOS VECES. En producción
    # eso es el doble de volumen de logs por nada.
    #
    # El SQL sigue viéndose en desarrollo: configure_logging() pone
    # el logger `sqlalchemy.engine` en INFO fuera de producción, y
    # sale una sola vez por nuestro handler.
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """
    La fábrica de sesiones, como dependencia.

    La necesitan los endpoints que viven más que su propia petición
    (el stream SSE): no pueden quedarse con la sesión de `get_db`
    porque eso retiene una conexión del pool durante minutos. Al ser
    una dependencia, los tests la sobreescriben igual que `get_db`.
    """
    return AsyncSessionLocal
