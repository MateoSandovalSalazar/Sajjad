"""
Transactional email via aiosmtplib.

All templates are inline strings to avoid filesystem
dependency in Docker images. Keep HTML minimal and
readable on mobile.
"""

import html
import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)


def _esc(value: object) -> str:
    """
    Escapa un valor antes de meterlo en el HTML del correo.

    `full_name` y `company` los escribe el usuario y acababan
    interpolados tal cual en la plantilla: un nombre como
    `<img src=x onerror=...>` se convertía en marcado dentro del
    correo. Que la víctima sea quien lo escribió no lo hace correcto:
    el nombre también viaja en avisos que puede leer otra persona.
    """
    return html.escape(str(value), quote=True)


async def _send(
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    settings = get_settings()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        use_tls=settings.smtp_tls,
        start_tls=settings.smtp_starttls,
    )

    logger.info("Email sent: %s → %s", subject, to_email)


def _base_template(title: str, body: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width">
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont,
            'Segoe UI', sans-serif; background: #0f172a;
            margin: 0; padding: 40px 20px; }}
    .card {{ background: #1e293b; border-radius: 12px;
             max-width: 520px; margin: 0 auto; padding: 40px; }}
    .logo {{ font-size: 24px; font-weight: 700;
             color: #38bdf8; margin-bottom: 32px; }}
    h1 {{ color: #f1f5f9; font-size: 22px; margin: 0 0 16px; }}
    p {{ color: #94a3b8; line-height: 1.6; margin: 0 0 24px; }}
    .btn {{ display: inline-block; background: #0ea5e9;
            color: #fff; text-decoration: none;
            padding: 14px 28px; border-radius: 8px;
            font-weight: 600; font-size: 15px; }}
    .footer {{ color: #475569; font-size: 13px;
               margin-top: 32px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">⚡ Sajjad</div>
    {body}
    <div class="footer">
      Si no solicitaste esto, puedes ignorar este correo.
      <br>© {datetime.now(timezone.utc).year} Sajjad —
      External Attack Surface Management
    </div>
  </div>
</body>
</html>
"""


async def send_verification_email(
    email: str,
    full_name: str,
    token: str,
) -> None:
    settings = get_settings()
    link = f"{settings.frontend_url}/verify-email?token={token}"

    body = f"""
<h1>Verifica tu correo</h1>
<p>Hola {_esc(full_name)},</p>
<p>Gracias por registrarte en Sajjad. Haz clic en el botón
para verificar tu correo y activar tu cuenta.</p>
<a href="{link}" class="btn">Verificar correo</a>
<p>O copia este enlace en tu navegador:<br>
<small style="color:#64748b">{link}</small></p>
"""
    body_html = _base_template("Verifica tu correo — Sajjad", body)
    await _send(email, "Verifica tu correo en Sajjad", body_html)


async def send_password_reset_email(
    email: str,
    full_name: str,
    token: str,
) -> None:
    settings = get_settings()
    link = f"{settings.frontend_url}/reset-password?token={token}"

    body = f"""
<h1>Restablecer contraseña</h1>
<p>Hola {_esc(full_name)},</p>
<p>Recibimos una solicitud para restablecer tu contraseña.
Este enlace expira en 1 hora.</p>
<a href="{link}" class="btn">Restablecer contraseña</a>
<p>O copia este enlace:<br>
<small style="color:#64748b">{link}</small></p>
"""
    body_html = _base_template(
        "Restablecer contraseña — Sajjad", body
    )
    await _send(email, "Restablece tu contraseña en Sajjad", body_html)


async def send_scan_complete_email(
    email: str,
    full_name: str,
    domain: str,
    risk_score: int,
    risk_level: str,
    critical_count: int,
    high_count: int,
) -> None:
    level_color = {
        "critical": "#ef4444",
        "high": "#f97316",
        "medium": "#eab308",
        "low": "#22c55e",
    }.get(risk_level, "#94a3b8")

    body = f"""
<h1>Escaneo completado</h1>
<p>Hola {_esc(full_name)},</p>
<p>El escaneo de <strong style="color:#38bdf8">{_esc(domain)}</strong>
ha finalizado.</p>
<div style="background:#0f172a;border-radius:8px;padding:20px;
            margin:20px 0;text-align:center;">
  <div style="font-size:48px;font-weight:700;
              color:{level_color};">{int(risk_score)}</div>
  <div style="color:#94a3b8;font-size:14px;text-transform:uppercase;
              letter-spacing:2px;">{_esc(risk_level)} RISK</div>
</div>
<p>Se encontraron <strong style="color:#ef4444">
{int(critical_count)} críticos</strong> y
<strong style="color:#f97316">{int(high_count)} altos</strong>.</p>
<p>Accede a tu dashboard para ver el reporte completo.</p>
"""
    body_html = _base_template("Escaneo completado — Sajjad", body)
    # El asunto es una cabecera MIME: un salto de línea en `domain`
    # permitiría inyectar cabeceras propias en el mensaje.
    safe_domain = domain.replace("\r", "").replace("\n", "")[:120]
    await _send(
        email,
        f"[Sajjad] Escaneo de {safe_domain} completado — "
        f"{risk_level.upper()}",
        body_html,
    )
