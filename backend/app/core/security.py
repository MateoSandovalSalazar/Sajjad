from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return _encode({"sub": subject, "type": "access", "exp": expire})


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    return _encode({"sub": subject, "type": "refresh", "exp": expire})


def create_email_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    return _encode({
        "sub": subject,
        "type": "email",
        "exp": expire,
    })


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.api_secret_key,
            algorithms=[ALGORITHM],
        )
    except JWTError:
        return {}


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(
        payload,
        settings.api_secret_key,
        algorithm=ALGORITHM,
    )
