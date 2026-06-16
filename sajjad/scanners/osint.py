"""
Stage 8 — OSINT Enrichment

Queries external data sources for passive intelligence:
  - Have I Been Pwned: credential breaches per domain
  - GitHub API: exposed secrets in public repositories
  - Shodan: internet-wide scan data for discovered IPs

All API keys are optional — missing keys skip that source.
"""

import logging
import os
from typing import Any

import httpx

from sajjad.models.finding import Finding

logger = logging.getLogger(__name__)

HIBP_BASE = "https://haveibeenpwned.com/api/v3"
GITHUB_API = "https://api.github.com"
SHODAN_API = "https://api.shodan.io"

REQUEST_TIMEOUT = 20.0


def enrich(
    domain: str,
    ips: list[str] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []

    findings.extend(_check_hibp(domain))
    findings.extend(_check_github(domain))

    if ips:
        for ip in ips[:10]:
            findings.extend(_check_shodan(ip))

    logger.info(
        "OSINT enrichment for %s: %d findings", domain, len(findings)
    )
    return findings


def _check_hibp(domain: str) -> list[Finding]:
    api_key = os.getenv("HIBP_API_KEY", "")
    if not api_key:
        logger.info("HIBP_API_KEY not set — skipping breach check")
        return []

    headers = {
        "hibp-api-key": api_key,
        "user-agent": "Sajjad-EASM/0.1",
    }
    url = f"{HIBP_BASE}/breacheddomain/{domain}"

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, headers=headers)

        if resp.status_code == 404:
            logger.info("HIBP: no breaches found for %s", domain)
            return []
        if resp.status_code == 401:
            logger.warning("HIBP: invalid API key")
            return []
        resp.raise_for_status()

        data: dict[str, list[str]] = resp.json()
        return _hibp_to_findings(domain, data)

    except httpx.HTTPError as exc:
        logger.warning("HIBP query failed for %s: %s", domain, exc)
        return []


def _hibp_to_findings(
    domain: str,
    data: dict[str, list[str]],
) -> list[Finding]:
    findings: list[Finding] = []
    total_accounts = len(data)

    if total_accounts == 0:
        return []

    sample = list(data.keys())[:5]
    all_breaches: set[str] = set()
    for breaches in data.values():
        all_breaches.update(breaches)

    findings.append(Finding(
        category="cred",
        severity="critical",
        title=(
            f"{total_accounts} cuentas de @{domain} "
            "encontradas en brechas de datos"
        ),
        description=(
            f"Have I Been Pwned reporta {total_accounts} cuentas "
            f"del dominio @{domain} expuestas en brechas conocidas: "
            f"{', '.join(sorted(all_breaches)[:5])}."
        ),
        evidence={
            "domain": domain,
            "total_accounts": total_accounts,
            "sample_accounts": sample,
            "breaches": sorted(all_breaches),
        },
        recommendation=(
            "Forzar cambio de contraseña para todas las cuentas "
            "afectadas. Habilitar MFA. Revisar si las credenciales "
            "filtradas se reutilizan en sistemas internos."
        ),
        source_tool="hibp",
        host=domain,
    ))

    return findings


def _check_github(domain: str) -> list[Finding]:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        logger.info("GITHUB_TOKEN not set — skipping GitHub search")
        return []

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sajjad-EASM/0.1",
    }
    queries = [
        f'"{domain}" password',
        f'"{domain}" api_key',
        f'"{domain}" secret',
        f'"{domain}" token',
    ]
    findings: list[Finding] = []

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            for query in queries:
                results = _github_code_search(
                    client, headers, query, domain
                )
                findings.extend(results)
    except httpx.HTTPError as exc:
        logger.warning("GitHub search failed: %s", exc)

    return findings


def _github_code_search(
    client: httpx.Client,
    headers: dict[str, str],
    query: str,
    domain: str,
) -> list[Finding]:
    resp = client.get(
        f"{GITHUB_API}/search/code",
        headers=headers,
        params={"q": query, "per_page": 5},
    )

    if resp.status_code == 403:
        logger.warning("GitHub: rate limited or insufficient permissions")
        return []
    if resp.status_code != 200:
        return []

    data = resp.json()
    total = data.get("total_count", 0)

    if total == 0:
        return []

    items = data.get("items", [])
    repos = list({
        item.get("repository", {}).get("full_name", "")
        for item in items
        if item.get("repository", {}).get("full_name")
    })

    return [Finding(
        category="osint",
        severity="high",
        title=(
            f"Posibles secretos con '{domain}' en GitHub "
            f"({total} resultados)"
        ),
        description=(
            f"La búsqueda en GitHub con la query {query!r} "
            f"devuelve {total} resultados que referencian "
            f"el dominio {domain}. Puede incluir credenciales "
            "o tokens expuestos."
        ),
        evidence={
            "query": query,
            "total_results": total,
            "sample_repos": repos[:5],
        },
        recommendation=(
            "Revisar manualmente los repositorios encontrados. "
            "Revocar cualquier credencial expuesta de inmediato. "
            "Usar git-secrets o truffleHog para auditoría local."
        ),
        source_tool="github_api",
        host=domain,
    )]


def _check_shodan(ip: str) -> list[Finding]:
    api_key = os.getenv("SHODAN_API_KEY", "")
    if not api_key:
        return []

    url = f"{SHODAN_API}/shodan/host/{ip}"
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, params={"key": api_key})

        if resp.status_code == 404:
            return []
        if resp.status_code != 200:
            logger.warning("Shodan returned %d for %s", resp.status_code, ip)
            return []

        data = resp.json()
        return _shodan_to_findings(ip, data)

    except httpx.HTTPError as exc:
        logger.warning("Shodan query failed for %s: %s", ip, exc)
        return []


def _shodan_to_findings(
    ip: str,
    data: dict[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []

    vulns = data.get("vulns", {})
    if vulns:
        cve_list = list(vulns.keys())[:10]
        critical_cves = [
            cve for cve, detail in vulns.items()
            if isinstance(detail, dict)
            and float(detail.get("cvss", 0)) >= 9.0
        ]

        severity = "critical" if critical_cves else "high"
        findings.append(Finding(
            category="vuln",
            severity=severity,
            title=(
                f"Shodan: {len(vulns)} CVEs conocidos en {ip}"
            ),
            description=(
                f"Shodan identifica {len(vulns)} vulnerabilidades "
                f"en {ip}: {', '.join(cve_list)}."
            ),
            evidence={
                "ip": ip,
                "cves": list(vulns.keys()),
                "critical_cves": critical_cves,
                "country": data.get("country_name", ""),
                "org": data.get("org", ""),
                "open_ports": data.get("ports", []),
            },
            recommendation=(
                "Revisar y parchear los CVEs listados. "
                "Priorizar según CVSS score."
            ),
            source_tool="shodan",
            host=ip,
        ))

    return findings
