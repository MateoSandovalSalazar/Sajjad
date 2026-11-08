"""
Authentication service — register, login, email verify,
password reset. All database writes go through here.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.exceptions import Conflict, NotFound, Unauthorized
from app.core.limits import FREE_PLAN, TRIAL_PLAN
from app.core.security import (
    create_access_token,
    create_email_token,
    create_refresh_token,
    decode_token,
    dummy_verify,
    hash_password,
    verify_password,
)
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenResponse
from app.services.email import send_verification_email


async def register_user(
    payload: RegisterRequest,
    db: AsyncSession,
) -> User:
    existing = await db.execute(
        select(User).where(User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise Conflict("Email already registered.")

    verification_token = str(uuid.uuid4())

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        company=payload.company,
        email_verification_token=verification_token,
    )
    db.add(user)

    # Free plan subscription created automatically
    sub = Subscription(
        user=user,
        plan="free",
        status=SubscriptionStatus.ACTIVE,
    )
    db.add(sub)

    # Commit antes de enviar el email: el usuario queda persistido y
    # disponible para login inmediato, aunque el envío del correo falle.
    await db.commit()

    try:
        await send_verification_email(
            user.email, user.full_name, verification_token
        )
    except Exception:
        # Email failure must not block registration
        pass

    return user


async def login_user(
    email: str,
    password: str,
    db: AsyncSession,
) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Gasta el mismo tiempo de bcrypt que si el usuario existiera:
        # si no, el tiempo de respuesta revela qué emails están
        # registrados y la base de usuarios queda enumerable.
        dummy_verify()
        raise Unauthorized("Incorrect email or password.")

    if not verify_password(password, user.hashed_password):
        raise Unauthorized("Incorrect email or password.")

    if not user.is_active:
        raise Unauthorized("Account is disabled.")

    return _build_tokens(user)


async def refresh_access_token(
    refresh_token: str,
    db: AsyncSession,
) -> TokenResponse:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise Unauthorized("Invalid token type.")

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise Unauthorized()

    # Un refresh token emitido antes del último cambio de contraseña
    # ya no vale.
    if payload.get("tv", 0) != user.token_version:
        raise Unauthorized("Session expired. Please log in again.")

    return _build_tokens(user)


async def verify_email(token: str, db: AsyncSession) -> User:
    result = await db.execute(
        select(User)
        .where(User.email_verification_token == token)
        .options(selectinload(User.subscription))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFound("Invalid or expired verification token.")

    already_verified = user.is_verified

    user.is_verified = True
    user.email_verification_token = None

    # La prueba gratuita se otorga aquí y no en el registro: exigir un
    # email verificado evita que se abran cuentas desechables en masa
    # para encadenar trials.
    if not already_verified:
        _start_trial(user.subscription)

    return user


def _start_trial(sub: Subscription | None) -> None:
    """
    Arranca la prueba gratuita si corresponde.

    Sólo se otorga a una suscripción free y sin trial previo, de modo
    que reverificar el email o un usuario que ya pagó nunca pierdan
    ni reciclen el plan.
    """
    settings = get_settings()
    if settings.trial_days <= 0 or sub is None:
        return
    if sub.plan != FREE_PLAN or sub.trial_ends_at is not None:
        return

    now = datetime.now(timezone.utc)
    sub.plan = TRIAL_PLAN
    sub.status = SubscriptionStatus.ACTIVE
    sub.trial_ends_at = now + timedelta(days=settings.trial_days)


async def request_password_reset(
    email: str,
    db: AsyncSession,
) -> None:
    """Always succeeds silently to prevent email enumeration."""
    from app.services.email import send_password_reset_email

    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return

    token = create_email_token(str(user.id))
    user.password_reset_token = token

    try:
        await send_password_reset_email(
            user.email, user.full_name, token
        )
    except Exception:
        pass


async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession,
) -> None:
    payload = decode_token(token)
    if payload.get("type") != "email":
        raise Unauthorized("Invalid token.")

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None or user.password_reset_token != token:
        raise Unauthorized("Token already used or invalid.")

    user.hashed_password = hash_password(new_password)
    user.password_reset_token = None
    # Invalida toda sesión abierta. Si la cuenta estaba comprometida,
    # cambiar la contraseña tiene que echar al atacante: sin esto su
    # refresh token seguiría sirviendo hasta 30 días.
    user.token_version += 1


def _build_tokens(user: User) -> TokenResponse:
    sub = str(user.id)
    return TokenResponse(
        access_token=create_access_token(sub, user.token_version),
        refresh_token=create_refresh_token(sub, user.token_version),
        token_type="bearer",
        user_id=str(user.id),
        email=user.email,
        is_verified=user.is_verified,
    )
