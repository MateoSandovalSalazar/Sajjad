"""
FastAPI dependency injection layer.

All auth, plan enforcement, and DB session management
live here so routers stay thin and readable.
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    Forbidden,
    PlanLimitExceeded,
    Unauthorized,
)
from app.core.security import decode_token, subject_uuid
from app.database import get_db, get_sessionmaker
from app.models import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None:
        raise Unauthorized()

    payload = decode_token(credentials.credentials)
    user_id = subject_uuid(payload)
    token_type: str | None = payload.get("type")

    if user_id is None or token_type != "access":
        raise Unauthorized()

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.subscription))
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise Unauthorized()

    # Un token emitido antes del último cambio de contraseña queda
    # invalidado, aunque todavía no haya expirado.
    if payload.get("tv", 0) != user.token_version:
        raise Unauthorized("Session expired. Please log in again.")

    return user


async def require_verified(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_verified:
        raise Forbidden(
            "Email not verified. Check your inbox for the "
            "verification link."
        )
    return user


def require_plan(*allowed_plans: str):
    """
    Returns a dependency that enforces the user has one of
    the given plan names with an active subscription.
    """
    async def _check(
        user: Annotated[User, Depends(require_verified)],
    ) -> User:
        plan = user.plan
        if allowed_plans and plan not in allowed_plans:
            raise PlanLimitExceeded(
                f"This feature requires one of: "
                f"{', '.join(allowed_plans)}. "
                f"Your current plan: {plan}."
            )
        return user

    return _check


async def get_current_plan(
    user: Annotated[User, Depends(get_current_user)],
) -> str:
    return user.plan


# ── Convenience type aliases ────────────────────────────
CurrentUser = Annotated[User, Depends(get_current_user)]
VerifiedUser = Annotated[User, Depends(require_verified)]
DB = Annotated[AsyncSession, Depends(get_db)]
# Para endpoints que necesitan abrir sesiones propias y cortas en vez
# de retener la de la petición (ver el stream SSE de scans).
SessionFactory = Annotated[
    async_sessionmaker[AsyncSession], Depends(get_sessionmaker)
]
