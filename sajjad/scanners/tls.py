"""
Stage 5 — TLS Certificate Analysis

Uses tlsx to inspect certificate validity, expiry,
cipher suites, and SAN entries for all HTTPS hosts.
"""

import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

from sajjad.models.finding import Finding

from . import parse_jsonl, run_tool

logger = logging.getLogger(__name__)

WEAK_CIPHERS = {
    "TLS_RSA_WITH_RC4_128_SHA",
    "TLS_RSA_WITH_RC4_128_MD5",
    "SSL_CK_RC4_128_WITH_MD5",
    "TLS_RSA_EXPORT_WITH_RC4_40_MD5",
    "TLS_RSA_WITH_3DES_EDE_CBC_SHA",
    "TLS_NULL_WITH_NULL_NULL",
}

WEAK_TLS_VERSIONS = {"ssl30", "tls10", "tls11"}


def analyze_tls(
    hosts: list[str],
    timeout: int = 120,
) -> list[Finding]:
    if not hosts:
        return []

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp:
        tmp.write("\n".join(hosts))
        tmp_path = tmp.name

    try:
        cmd = [
            "tlsx",
            "-l", tmp_path,
            "-json", "-silent",
            "-expired",
            "-self-signed",
            "-mismatched",
            # -san conflicts with probe flags in this tlsx version
        ]
        output = run_tool(cmd, timeout=timeout)
        records = parse_jsonl(output)
        logger.info(
            "tlsx: %d TLS records for %d hosts",
            len(records),
            len(hosts),
        )
        return _build_findings(records)
    finally:
        os.unlink(tmp_path)


def _build_findings(
    records: list[dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []

    for rec in records:
        host = rec.get("host", "")
        findings.extend(_check_expiry(rec, host))
        findings.extend(_check_self_signed(rec, host))
        findings.extend(_check_tls_version(rec, host))
        findings.extend(_check_cipher(rec, host))

    logger.info("TLS analysis: %d findings", len(findings))
    return findings


def _check_expiry(
    rec: dict[str, Any],
    host: str,
) -> list[Finding]:
    not_after_raw = rec.get("not_after", "")
    if not not_after_raw:
        return []

    try:
        not_after = datetime.fromisoformat(
            not_after_raw.replace("Z", "+00:00")
        )
    except ValueError:
        return []

    now = datetime.now(timezone.utc)
    days_left = (not_after - now).days

    if rec.get("expired") or days_left <= 0:
        return [Finding(
            category="cert",
            severity="high",
            title=f"Certificado TLS vencido en {host}",
            description=(
                f"El certificado SSL/TLS de {host} venció "
                f"hace {abs(days_left)} días ({not_after_raw}). "
                "Los navegadores mostrarán advertencia de seguridad."
            ),
            evidence={
                "host": host,
                "not_after": not_after_raw,
                "days_expired": abs(days_left),
            },
            recommendation=(
                "Renovar el certificado TLS inmediatamente. "
                "Considerar Let's Encrypt con auto-renovación "
                "vía certbot o acme.sh."
            ),
            source_tool="tlsx",
            host=host,
        )]

    if 0 < days_left <= 30:
        return [Finding(
            category="cert",
            severity="medium",
            title=(
                f"Certificado por vencer en {days_left} días: {host}"
            ),
            description=(
                f"El certificado de {host} vence en {days_left} días "
                f"({not_after_raw}). Sin renovación habrá downtime."
            ),
            evidence={
                "host": host,
                "not_after": not_after_raw,
                "days_remaining": days_left,
            },
            recommendation=(
                "Renovar el certificado antes del vencimiento. "
                "Implementar auto-renovación para evitar esto."
            ),
            source_tool="tlsx",
            host=host,
        )]

    return []


def _check_self_signed(
    rec: dict[str, Any],
    host: str,
) -> list[Finding]:
    if not rec.get("self_signed"):
        return []

    return [Finding(
        category="cert",
        severity="medium",
        title=f"Certificado auto-firmado en {host}",
        description=(
            f"{host} usa un certificado auto-firmado. "
            "No es confiable para clientes externos y "
            "genera alertas de seguridad en navegadores."
        ),
        evidence={"host": host, "self_signed": True},
        recommendation=(
            "Reemplazar con un certificado emitido por una CA "
            "de confianza pública (Let's Encrypt, DigiCert, etc.)."
        ),
        source_tool="tlsx",
        host=host,
    )]


def _check_tls_version(
    rec: dict[str, Any],
    host: str,
) -> list[Finding]:
    version = rec.get("tls_version", "").lower()
    if version not in WEAK_TLS_VERSIONS:
        return []

    label = version.upper().replace("TLS", "TLS ")
    return [Finding(
        category="cert",
        severity="high",
        title=f"Versión TLS obsoleta ({label}) en {host}",
        description=(
            f"{host} acepta conexiones con {label}, "
            "una versión obsoleta con vulnerabilidades conocidas "
            "(POODLE, BEAST, etc.)."
        ),
        evidence={"host": host, "tls_version": version},
        recommendation=(
            "Deshabilitar SSLv3, TLS 1.0 y TLS 1.1. "
            "Configurar el servidor para requerir TLS 1.2+ "
            "y preferir TLS 1.3."
        ),
        source_tool="tlsx",
        host=host,
    )]


def _check_cipher(
    rec: dict[str, Any],
    host: str,
) -> list[Finding]:
    cipher = rec.get("cipher", "")
    if cipher not in WEAK_CIPHERS:
        return []

    return [Finding(
        category="cert",
        severity="high",
        title=f"Cipher suite débil ({cipher}) en {host}",
        description=(
            f"{host} usa el cipher suite {cipher!r}, "
            "considerado criptográficamente débil."
        ),
        evidence={"host": host, "cipher": cipher},
        recommendation=(
            "Actualizar la configuración TLS para usar únicamente "
            "cipher suites modernos (AES-GCM, ChaCha20-Poly1305)."
        ),
        source_tool="tlsx",
        host=host,
    )]
