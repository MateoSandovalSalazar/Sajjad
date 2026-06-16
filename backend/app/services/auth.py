"""
Authentication service — register, login, email verify,
password reset. All database writes go through here.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound, Unauthorized
from app.core.security import (
    create_access_token,
    create_email_token,
    create_refresh_token,
    decode_token,
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

    await db.flush()  # get user.id without committing

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

    if user is None or not verify_password(
        password, user.hashed_password
    ):
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

    return _build_tokens(user)


async def verify_email(token: str, db: AsyncSession) -> User:
    result = await db.execute(
        select(User).where(User.email_verification_token == token)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFound("Invalid or expired verification token.")

    user.is_verified = True
    user.email_verification_token = None
    return user


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


def _build_tokens(user: User) -> TokenResponse:
    sub = str(user.id)
    return TokenResponse(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
        token_type="bearer",
        user_id=str(user.id),
        email=user.email,
        is_verified=user.is_verified,
    )
