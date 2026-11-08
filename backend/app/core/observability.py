"""
Observabilidad: logging estructurado y reporte de errores.

Dos piezas independientes, ambas opcionales por configuración:

1. Logging JSON. En producción los logs los lee una máquina (grep,
   journald, un agregador), no una persona. Un formato de una línea
   por evento con campos fijos se filtra y se correlaciona; el
   formato humano de desarrollo no.

2. Sentry. Se activa sólo si hay SENTRY_DSN. Sin DSN, todo esto es
   un no-op y el proyecto no arrastra dependencia obligatoria.
"""

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

from app.config import get_settings

# Se rellena en el middleware de request-id y viaja implícitamente
# a todos los logs de esa petición: así una traza de error se puede
# atar al request concreto que la provocó.
request_id_ctx: ContextVar[str | None] = ContextVar(
    "request_id", default=None
)

# Campos propios de LogRecord que ya emitimos explícitamente o que
# no aportan nada en JSON. Todo lo demás que traiga el record se
# considera contexto extra y se incluye.
_RESERVED = frozenset({
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName",
    "taskName",
})


class JsonFormatter(logging.Formatter):
    """Una línea JSON por evento de log."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        rid = request_id_ctx.get()
        if rid:
            payload["request_id"] = rid

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """
    Configura el logging del proceso.

    JSON en producción, formato legible en desarrollo. Reemplaza los
    handlers existentes para que basicConfig() llamado antes por
    cualquier import no deje un handler duplicado escupiendo cada
    línea dos veces.
    """
    settings = get_settings()

    handler = logging.StreamHandler(sys.stdout)
    if settings.is_production:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-8s %(name)s %(message)s"
            )
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # SQLAlchemy con echo=True es utilísimo en desarrollo e
    # insoportable en producción.
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if settings.is_production else logging.INFO
    )


def configure_sentry() -> bool:
    """
    Inicializa Sentry si hay DSN configurado.

    Devuelve True si quedó activo. Nunca lanza: un fallo montando el
    reporte de errores no puede impedir que la API arranque.
    """
    settings = get_settings()
    if not settings.sentry_dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import (
            SqlalchemyIntegration,
        )

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.api_env,
            release=settings.release_version,
            integrations=[
                FastApiIntegration(),
                CeleryIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=settings.sentry_traces_sample_rate,
            # Sajjad maneja infraestructura ajena: nunca enviar
            # cuerpos de petición, cabeceras ni datos de usuario a un
            # tercero. Sólo el error y su traza.
            send_default_pii=False,
            max_request_body_size="never",
            before_send=_scrub_event,
        )
        logging.getLogger(__name__).info(
            "Sentry activo (entorno=%s)", settings.api_env
        )
        return True
    except ImportError:
        logging.getLogger(__name__).warning(
            "SENTRY_DSN configurado pero sentry-sdk no está instalado. "
            "Instala el extra: uv sync --extra monitoring"
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).error(
            "No se pudo inicializar Sentry: %s", exc
        )
        return False


_SENSITIVE_KEYS = frozenset({
    "password", "new_password", "current_password", "token",
    "access_token", "refresh_token", "authorization", "cookie",
    "api_secret_key", "mp_access_token", "mp_webhook_secret",
    "hashed_password", "verification_token", "password_reset_token",
    "hibp_api_key", "github_token", "shodan_api_key",
})


def _scrub_event(event: dict, hint: dict) -> dict:
    """
    Última red de seguridad antes de enviar nada a Sentry.

    `send_default_pii=False` ya evita lo obvio, pero un secreto puede
    colarse en el valor de una variable local de una traza. Esto
    recorre el evento entero y enmascara cualquier clave sensible.
    """
    def _walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: (
                    "[REDACTADO]"
                    if isinstance(k, str) and k.lower() in _SENSITIVE_KEYS
                    else _walk(v)
                )
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_walk(v) for v in obj]
        return obj

    return _walk(event)
