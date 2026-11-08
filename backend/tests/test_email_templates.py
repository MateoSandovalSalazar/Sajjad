"""
Tests de las plantillas de correo.

El nombre y la empresa los escribe el usuario y acaban dentro del HTML
del mensaje. Sin escapar, un nombre como `<img src=x onerror=...>` se
convierte en marcado en el correo; y un salto de línea en el asunto
permite inyectar cabeceras MIME.
"""

from datetime import datetime, timezone

import pytest

from app.services import email as email_service

# El fixture autouse del conftest sustituye send_password_reset_email
# por un noop para que ningún test mande correos. Aquí sí queremos la
# función de verdad, así que se guarda la referencia real al importar
# el módulo —antes de que los fixtures corran— y se restaura abajo.
_REAL_PASSWORD_RESET = email_service.send_password_reset_email


@pytest.fixture
def capturado(monkeypatch):
    """Intercepta _send y devuelve lo que se habría enviado."""
    enviado: dict = {}

    async def _fake_send(to_email, subject, html_body):
        enviado.update(
            to=to_email, subject=subject, html=html_body
        )

    monkeypatch.setattr(email_service, "_send", _fake_send)
    monkeypatch.setattr(
        email_service,
        "send_password_reset_email",
        _REAL_PASSWORD_RESET,
    )
    return enviado


@pytest.mark.asyncio
async def test_nombre_con_html_se_escapa(capturado):
    await email_service.send_verification_email(
        "v@example.com",
        '<img src=x onerror="alert(1)">',
        "tok-123",
    )
    html = capturado["html"]
    assert "<img src=x" not in html
    assert "&lt;img src=x" in html


@pytest.mark.asyncio
async def test_nombre_con_html_se_escapa_en_reset(capturado):
    await email_service.send_password_reset_email(
        "v@example.com", "<script>robar()</script>", "tok-123"
    )
    html = capturado["html"]
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


@pytest.mark.asyncio
async def test_dominio_con_html_se_escapa_en_aviso(capturado):
    await email_service.send_scan_complete_email(
        email="v@example.com",
        full_name="Ana",
        domain="<b>malo.com</b>",
        risk_score=73,
        risk_level="high",
        critical_count=1,
        high_count=2,
    )
    html = capturado["html"]
    assert "<b>malo.com</b>" not in html
    assert "&lt;b&gt;malo.com" in html


@pytest.mark.asyncio
async def test_asunto_sin_saltos_de_linea(capturado):
    """Un \\n en el dominio no debe partir la cabecera del asunto."""
    await email_service.send_scan_complete_email(
        email="v@example.com",
        full_name="Ana",
        domain="bueno.com\nBcc: victima@example.com",
        risk_score=10,
        risk_level="low",
        critical_count=0,
        high_count=0,
    )
    assert "\n" not in capturado["subject"]
    assert "\r" not in capturado["subject"]
    assert "Bcc:" in capturado["subject"]  # queda inerte, en una línea


@pytest.mark.asyncio
async def test_enlace_de_verificacion_apunta_al_frontend(capturado):
    await email_service.send_verification_email(
        "v@example.com", "Ana", "tok-abc"
    )
    assert "/verify-email?token=tok-abc" in capturado["html"]


@pytest.mark.asyncio
async def test_enlace_de_reset_apunta_a_la_ruta_que_existe(capturado):
    """
    El correo enlaza a /reset-password; esa ruta tiene que existir en el
    frontend (App.tsx). Si se renombra una de las dos, el usuario
    termina en la landing sin saber por qué.
    """
    await email_service.send_password_reset_email(
        "v@example.com", "Ana", "tok-abc"
    )
    assert "/reset-password?token=tok-abc" in capturado["html"]


@pytest.mark.asyncio
async def test_pie_con_el_anio_actual(capturado):
    """El pie tenía 2025 escrito a mano."""
    await email_service.send_verification_email(
        "v@example.com", "Ana", "tok"
    )
    anio = datetime.now(timezone.utc).year
    assert f"© {anio} Sajjad" in capturado["html"]
