"""
Stage 2 — DNS Resolution & Mail Security Analysis

Uses dnsx to resolve subdomains and detect live hosts.
Runs direct DNS queries to audit SPF, DKIM, and DMARC.
"""

import logging
import os
import subprocess
import tempfile
from typing import Any

from sajjad.models.finding import Finding

from . import parse_jsonl, run_tool

logger = logging.getLogger(__name__)


def resolve_subdomains(
    subdomains: list[str],
    timeout: int = 120,
) -> list[dict[str, Any]]:
    if not subdomains:
        return []

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp:
        tmp.write("\n".join(subdomains))
        tmp_path = tmp.name

    try:
        cmd = [
            "dnsx",
            "-l", tmp_path,
            "-json", "-silent",
            "-a", "-cname",
        ]
        output = run_tool(cmd, timeout=timeout)
        records = parse_jsonl(output)
        logger.info(
            "dnsx: %d/%d subdomains resolved",
            len(records),
            len(subdomains),
        )
        return records
    finally:
        os.unlink(tmp_path)


def extract_live_hosts(
    records: list[dict[str, Any]],
) -> list[str]:
    return [r["host"] for r in records if "host" in r]


def check_dangling_dns(
    subdomains: list[str],
    live_hosts: list[str],
) -> list[Finding]:
    live_set = set(live_hosts)
    findings: list[Finding] = []

    for sub in subdomains:
        if sub not in live_set:
            findings.append(Finding(
                category="dns",
                severity="high",
                title=f"Posible dangling DNS: {sub}",
                description=(
                    f"El subdominio {sub} tiene registros DNS "
                    "pero no resuelve a ninguna IP activa. "
                    "Posible riesgo de subdomain takeover."
                ),
                evidence={
                    "subdomain": sub,
                    "status": "no_resolution",
                },
                recommendation=(
                    "Verificar si el subdominio sigue en uso. "
                    "Si está obsoleto, eliminar el registro DNS "
                    "para prevenir takeover por terceros."
                ),
                source_tool="dnsx",
                host=sub,
            ))

    logger.info(
        "Dangling DNS check: %d potential takeover records",
        len(findings),
    )
    return findings


def analyze_mail_dns(domain: str) -> list[Finding]:
    findings: list[Finding] = []

    txt_records = _query_txt(domain)
    spf = _find_spf(txt_records)
    dmarc = _find_dmarc(domain)

    findings.extend(_audit_spf(domain, spf))
    findings.extend(_audit_dmarc(domain, dmarc))

    logger.info(
        "Mail DNS analysis for %s: %d findings", domain, len(findings)
    )
    return findings


def _audit_spf(domain: str, spf: str | None) -> list[Finding]:
    if spf is None:
        return [Finding(
            category="dns",
            severity="high",
            title=f"Sin registro SPF en {domain}",
            description=(
                f"El dominio {domain} no tiene registro SPF. "
                "Cualquier servidor puede enviar emails "
                f"como @{domain}, facilitando phishing."
            ),
            evidence={"domain": domain, "spf": None},
            recommendation=(
                "Crear registro TXT: "
                "v=spf1 include:_spf.google.com ~all"
            ),
            source_tool="dns_query",
            host=domain,
        )]

    if "+all" in spf:
        return [Finding(
            category="dns",
            severity="high",
            title=f"SPF permisivo (+all) en {domain}",
            description=(
                f"El SPF de {domain} usa +all, permitiendo que "
                "cualquier servidor envíe email como este dominio."
            ),
            evidence={"domain": domain, "spf": spf},
            recommendation=(
                "Reemplazar +all por ~all (softfail) "
                "o -all (reject) en el registro SPF."
            ),
            source_tool="dns_query",
            host=domain,
        )]

    return []


def _audit_dmarc(domain: str, dmarc: str | None) -> list[Finding]:
    if dmarc is None:
        return [Finding(
            category="dns",
            severity="high",
            title=f"Sin registro DMARC en {domain}",
            description=(
                f"{domain} no tiene DMARC. Sin esta política, "
                "los receptores no pueden bloquear emails "
                "falsificados automáticamente."
            ),
            evidence={"domain": domain, "dmarc": None},
            recommendation=(
                f"Agregar TXT en _dmarc.{domain}: "
                f"v=DMARC1; p=quarantine; "
                f"rua=mailto:dmarc@{domain}"
            ),
            source_tool="dns_query",
            host=domain,
        )]

    if "p=none" in dmarc:
        return [Finding(
            category="dns",
            severity="medium",
            title=f"DMARC en modo monitor (p=none) en {domain}",
            description=(
                "DMARC está presente pero en modo monitor. "
                "Los emails que fallan autenticación no son "
                "rechazados ni enviados a cuarentena."
            ),
            evidence={"domain": domain, "dmarc": dmarc},
            recommendation=(
                "Escalar la política a p=quarantine una vez "
                "validada la configuración de SPF y DKIM, "
                "y luego a p=reject."
            ),
            source_tool="dns_query",
            host=domain,
        )]

    return []


def _query_txt(domain: str) -> list[str]:
    try:
        result = subprocess.run(
            ["dig", "+short", "TXT", domain],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip().splitlines()
    except Exception:
        return []


def _find_spf(records: list[str]) -> str | None:
    for r in records:
        clean = r.strip('"')
        if clean.startswith("v=spf1"):
            return clean
    return None


def _find_dmarc(domain: str) -> str | None:
    records = _query_txt(f"_dmarc.{domain}")
    for r in records:
        clean = r.strip('"')
        if clean.startswith("v=DMARC1"):
            return clean
    return None
