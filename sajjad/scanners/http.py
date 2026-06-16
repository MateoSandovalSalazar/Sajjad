"""
Stage 3 — HTTP Probing & Security Header Analysis

Runs ProjectDiscovery's httpx for live host detection,
then inspects HTTP response headers for security hygiene.
"""

import logging
import os
import tempfile
from typing import Any

import httpx

from sajjad.models.finding import Finding

from . import parse_jsonl, run_tool

logger = logging.getLogger(__name__)

# Headers that should be present in secure responses
REQUIRED_HEADERS: dict[str, dict[str, Any]] = {
    "strict-transport-security": {
        "title": "HSTS no configurado",
        "severity": "medium",
        "recommendation": (
            "Agregar: Strict-Transport-Security: "
            "max-age=31536000; includeSubDomains"
        ),
    },
    "x-content-type-options": {
        "title": "X-Content-Type-Options ausente",
        "severity": "low",
        "recommendation": (
            "Agregar: X-Content-Type-Options: nosniff"
        ),
    },
    "x-frame-options": {
        "title": "X-Frame-Options ausente",
        "severity": "medium",
        "recommendation": (
            "Agregar: X-Frame-Options: DENY o SAMEORIGIN"
        ),
    },
    "content-security-policy": {
        "title": "Content-Security-Policy ausente",
        "severity": "medium",
        "recommendation": (
            "Implementar una política CSP restrictiva. "
            "Comenzar con: Content-Security-Policy: "
            "default-src 'self'"
        ),
    },
    "referrer-policy": {
        "title": "Referrer-Policy ausente",
        "severity": "low",
        "recommendation": (
            "Agregar: Referrer-Policy: strict-origin-when-cross-origin"
        ),
    },
}

# Headers that reveal internal information
LEAKY_HEADERS = {
    "x-powered-by",
    "server",
    "x-aspnet-version",
    "x-aspnetmvc-version",
}


def probe_hosts(
    hosts: list[str],
    timeout: int = 120,
) -> list[dict[str, Any]]:
    if not hosts:
        return []

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp:
        tmp.write("\n".join(hosts))
        tmp_path = tmp.name

    try:
        cmd = [
            "httpx",
            "-l", tmp_path,
            "-json", "-silent",
            "-title",
            "-tech-detect",
            "-status-code",
            "-web-server",
            "-content-type",
            "-no-color",
        ]
        output = run_tool(cmd, timeout=timeout)
        records = parse_jsonl(output)
        logger.info(
            "httpx: %d/%d hosts responded",
            len(records),
            len(hosts),
        )
        return records
    finally:
        os.unlink(tmp_path)


def analyze_security_headers(
    http_results: list[dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []

    for record in http_results:
        url = record.get("url", "")
        host = record.get("input", url)

        # Only check HTTPS endpoints for HSTS; HTTP is expected to lack it
        if not url.startswith("https://"):
            subset = {
                k: v
                for k, v in REQUIRED_HEADERS.items()
                if k != "strict-transport-security"
            }
        else:
            subset = REQUIRED_HEADERS

        headers = _fetch_response_headers(url)
        if headers is None:
            continue

        lower_headers = {k.lower(): v for k, v in headers.items()}

        for header_name, meta in subset.items():
            if header_name not in lower_headers:
                findings.append(Finding(
                    category="vuln",
                    severity=meta["severity"],
                    title=f"{meta['title']} en {host}",
                    description=(
                        f"La respuesta HTTP de {url} no incluye "
                        f"el header de seguridad {header_name}."
                    ),
                    evidence={
                        "url": url,
                        "missing_header": header_name,
                        "present_headers": list(lower_headers.keys()),
                    },
                    recommendation=meta["recommendation"],
                    source_tool="httpx",
                    host=host,
                ))

        findings.extend(
            _check_leaky_headers(host, url, lower_headers)
        )

    logger.info(
        "Security header analysis: %d findings", len(findings)
    )
    return findings


def _fetch_response_headers(
    url: str,
) -> dict[str, str] | None:
    try:
        with httpx.Client(
            timeout=10,
            verify=False,
            follow_redirects=True,
            headers={"User-Agent": "Sajjad-Scanner/0.1"},
        ) as client:
            resp = client.head(url)
            return dict(resp.headers)
    except Exception as exc:
        logger.debug("Header fetch failed for %s: %s", url, exc)
        return None


def _check_leaky_headers(
    host: str,
    url: str,
    headers: dict[str, str],
) -> list[Finding]:
    findings: list[Finding] = []
    for header in LEAKY_HEADERS:
        value = headers.get(header)
        if value and _looks_verbose(value):
            findings.append(Finding(
                category="vuln",
                severity="low",
                title=f"Versión expuesta en header {header}: {host}",
                description=(
                    f"El header {header!r} revela información "
                    f"de versión: {value!r}. Esto facilita "
                    "el fingerprinting del servidor."
                ),
                evidence={
                    "url": url,
                    "header": header,
                    "value": value,
                },
                recommendation=(
                    f"Configurar el servidor para omitir o "
                    f"sanitizar el header {header!r}."
                ),
                source_tool="httpx",
                host=host,
            ))
    return findings


def _looks_verbose(value: str) -> bool:
    """True if the header value contains a version number."""
    import re
    return bool(re.search(r"\d+\.\d+", value))
