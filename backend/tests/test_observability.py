"""
Tests de observabilidad.

Lo importante aquí no es que el log se vea bonito, sino que nunca
salga un secreto hacia un servicio de terceros.
"""

import json
import logging

from app.core.observability import (
    JsonFormatter,
    _scrub_event,
    request_id_ctx,
)


def _record(msg: str, **extra) -> logging.LogRecord:
    record = logging.LogRecord(
        name="sajjad.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in extra.items():
        setattr(record, k, v)
    return record


def test_json_formatter_emits_one_line_of_json():
    out = JsonFormatter().format(_record("algo pasó"))
    parsed = json.loads(out)

    assert "\n" not in out
    assert parsed["message"] == "algo pasó"
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "sajjad.test"


def test_json_formatter_includes_extra_fields():
    out = JsonFormatter().format(
        _record("request", status=200, duration_ms=12.5)
    )
    parsed = json.loads(out)

    assert parsed["status"] == 200
    assert parsed["duration_ms"] == 12.5


def test_json_formatter_attaches_request_id():
    """
    El request-id correlaciona todas las líneas de una petición: sin
    él, investigar un incidente en producción es imposible.
    """
    token = request_id_ctx.set("req-abc-123")
    try:
        parsed = json.loads(JsonFormatter().format(_record("hola")))
        assert parsed["request_id"] == "req-abc-123"
    finally:
        request_id_ctx.reset(token)


def test_json_formatter_omits_request_id_outside_a_request():
    parsed = json.loads(JsonFormatter().format(_record("tarea beat")))
    assert "request_id" not in parsed


# ── Scrubbing de secretos ────────────────────────────────────


def test_scrub_redacts_secrets_at_any_depth():
    """
    Un secreto puede aparecer en las variables locales de una traza,
    no sólo en el cuerpo de la petición. El scrub recorre el evento
    entero.
    """
    event = {
        "request": {
            "data": {
                "email": "user@example.com",
                "password": "SuperSecreta123",
            }
        },
        "extra": {
            "config": {
                "mp_access_token": "APP_USR-real-token",
                "api_secret_key": "clave-de-firma-jwt",
            }
        },
        "exception": {
            "values": [
                {"vars": {"refresh_token": "eyJhbGciOi..."}}
            ]
        },
    }

    scrubbed = _scrub_event(event, {})

    assert scrubbed["request"]["data"]["password"] == "[REDACTADO]"
    assert (
        scrubbed["extra"]["config"]["mp_access_token"] == "[REDACTADO]"
    )
    assert (
        scrubbed["extra"]["config"]["api_secret_key"] == "[REDACTADO]"
    )
    assert (
        scrubbed["exception"]["values"][0]["vars"]["refresh_token"]
        == "[REDACTADO]"
    )

    # Y lo que no es secreto se conserva: si no, el reporte no sirve.
    assert scrubbed["request"]["data"]["email"] == "user@example.com"


def test_scrub_is_case_insensitive():
    scrubbed = _scrub_event(
        {"headers": {"Authorization": "Bearer xyz"}}, {}
    )
    assert scrubbed["headers"]["Authorization"] == "[REDACTADO]"


def test_scrub_handles_lists_and_scalars():
    event = {
        "breadcrumbs": [
            {"message": "login", "password": "abc"},
            {"message": "ok"},
        ],
        "level": "error",
    }
    scrubbed = _scrub_event(event, {})

    assert scrubbed["breadcrumbs"][0]["password"] == "[REDACTADO]"
    assert scrubbed["breadcrumbs"][1]["message"] == "ok"
    assert scrubbed["level"] == "error"


def test_sentry_disabled_without_dsn(monkeypatch):
    """Sin DSN no se inicializa nada y no se rompe el arranque."""
    from app.config import get_settings
    from app.core.observability import configure_sentry

    monkeypatch.delenv("SENTRY_DSN", raising=False)
    get_settings.cache_clear()
    try:
        assert configure_sentry() is False
    finally:
        get_settings.cache_clear()
