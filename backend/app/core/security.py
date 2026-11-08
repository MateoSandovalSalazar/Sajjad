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
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # Hash corrupto o con formato desconocido: no es válido, pero
        # tampoco debe tumbar la petición con un 500.
        return False


# Hash de descarte, calculado una sola vez al importar el módulo.
# Se usa para gastar el mismo tiempo de bcrypt cuando el email no
# existe — ver dummy_verify().
_DUMMY_HASH = bcrypt.hashpw(b"sajjad-dummy-password", bcrypt.gensalt())


def dummy_verify() -> None:
    """
    Quema un ciclo de bcrypt sin comprobar nada.

    Si el login sólo hiciera bcrypt cuando el usuario existe, las
    respuestas para emails registrados tardarían ~100 ms más que para
    los que no. Esa diferencia es trivial de medir y permite enumerar
    la base de usuarios. Llamando a esto en la rama "no existe", los
    dos caminos cuestan lo mismo.
    """
    bcrypt.checkpw(b"sajjad-dummy-password", _DUMMY_HASH)


def create_access_token(subject: str, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    return _encode({
        "sub": subject,
        "type": "access",
        "tv": token_version,
        "exp": expire,
    })


def create_refresh_token(subject: str, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    return _encode({
        "sub": subject,
        "type": "refresh",
        "tv": token_version,
        "exp": expire,
    })


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
