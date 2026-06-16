"""
Scan Orchestrator

Drives the 9-stage pipeline in sequence, passing results
between stages. Accepts an optional callback for live
progress updates (used by the CLI to render a status display).
"""

import logging
import os
import shutil
from typing import Callable

from sajjad.exceptions import ToolNotFoundError
from sajjad.models.finding import Finding
from sajjad.models.scan_result import ScanResult
from sajjad.scanners import dns, http, osint, ports, subdomain, tls, vulns
from sajjad.scanners import _resolve_binary
from sajjad.analysis import deduplicate, calculate_score
from sajjad.analysis.normalizer import normalize

logger = logging.getLogger(__name__)

REQUIRED_TOOLS = [
    "subfinder", "dnsx", "httpx",
    "naabu", "nmap", "tlsx", "nuclei",
]

ProgressCallback = Callable[[str, str], None]


def _tool_available(name: str) -> bool:
    resolved = _resolve_binary(name)
    if os.path.isfile(resolved):
        return True
    return shutil.which(name) is not None


def verify_tools() -> None:
    missing = [t for t in REQUIRED_TOOLS if not _tool_available(t)]
    if missing:
        raise ToolNotFoundError(
            "Missing required tools: "
            + ", ".join(missing)
            + ". Install them and ensure they are in PATH."
        )


class ScanOrchestrator:
    def __init__(
        self,
        domain: str,
        on_progress: ProgressCallback | None = None,
        scan_timeout: int = 300,
        nuclei_rate_limit: int = 150,
    ) -> None:
        self.domain = domain
        self.scan_timeout = scan_timeout
        self.nuclei_rate_limit = nuclei_rate_limit
        self._progress = on_progress or (lambda _s, _m: None)

    def run(self) -> ScanResult:
        result = ScanResult(domain=self.domain)
        all_findings: list[Finding] = []

        # ── Stage 1: Subdomain discovery ──────────────
        self._step("DISCOVERY", "Descubriendo subdominios…")
        subdomains = subdomain.discover_subdomains(
            self.domain, timeout=self.scan_timeout
        )
        result.subdomains = subdomains
        self._step(
            "DISCOVERY",
            f"{len(subdomains)} subdominios encontrados",
        )

        # ── Stage 2: DNS resolution ────────────────────
        self._step("DNS", f"Resolviendo {len(subdomains)} subdominios…")
        dns_records = dns.resolve_subdomains(
            subdomains, timeout=self.scan_timeout // 2
        )
        live_hosts = dns.extract_live_hosts(dns_records)
        result.live_hosts = live_hosts

        all_findings.extend(
            dns.check_dangling_dns(subdomains, live_hosts)
        )
        all_findings.extend(dns.analyze_mail_dns(self.domain))
        self._step(
            "DNS",
            f"{len(live_hosts)} hosts activos · "
            f"{len(all_findings)} hallazgos DNS",
        )

        # ── Stage 3: HTTP probing ──────────────────────
        self._step("HTTP", f"Probando {len(live_hosts)} hosts…")
        http_results = http.probe_hosts(
            live_hosts, timeout=self.scan_timeout // 2
        )
        http_findings = http.analyze_security_headers(http_results)
        all_findings.extend(http_findings)
        self._step(
            "HTTP",
            f"{len(http_results)} URLs activas · "
            f"{len(http_findings)} hallazgos HTTP",
        )

        # ── Stage 4: Port scanning ─────────────────────
        self._step("PORTS", f"Escaneando puertos en {len(live_hosts)} hosts…")
        port_map = ports.scan_ports(
            live_hosts, timeout=self.scan_timeout
        )
        result.open_ports = port_map
        port_findings = ports.analyze_ports(port_map)
        all_findings.extend(port_findings)
        total_ports = sum(len(v) for v in port_map.values())
        self._step(
            "PORTS",
            f"{total_ports} puertos abiertos · "
            f"{len(port_findings)} hallazgos",
        )

        # ── Stage 5: TLS analysis ──────────────────────
        https_hosts = [
            h for h, ps in port_map.items() if 443 in ps
        ] or live_hosts[:20]
        self._step("TLS", f"Analizando certificados en {len(https_hosts)} hosts…")
        tls_findings = tls.analyze_tls(
            https_hosts, timeout=self.scan_timeout // 2
        )
        all_findings.extend(tls_findings)
        self._step("TLS", f"{len(tls_findings)} hallazgos TLS")

        # ── Stage 6: Mail DNS already done in stage 2 ─

        # ── Stage 7: Vulnerability detection ──────────
        http_urls = [r["url"] for r in http_results if "url" in r]
        self._step(
            "VULNS",
            f"Ejecutando nuclei en {len(http_urls)} URLs…",
        )
        vuln_findings = vulns.scan_vulnerabilities(
            http_urls,
            timeout=self.scan_timeout * 2,
            rate_limit=self.nuclei_rate_limit,
        )
        all_findings.extend(vuln_findings)
        self._step("VULNS", f"{len(vuln_findings)} vulnerabilidades detectadas")

        # ── Stage 8: OSINT enrichment ──────────────────
        self._step("OSINT", "Enriqueciendo con fuentes externas…")
        all_ips = list({
            ip
            for ps in dns_records
            for ip in ps.get("a", [])
        })
        osint_findings = osint.enrich(self.domain, ips=all_ips)
        all_findings.extend(osint_findings)
        self._step("OSINT", f"{len(osint_findings)} hallazgos OSINT")

        # ── Stage 9: Normalize, deduplicate, score ─────
        self._step("ANALYSIS", "Normalizando y deduplicando hallazgos…")
        normalized = normalize(all_findings)
        unique = deduplicate(normalized)

        self._step("ANALYSIS", "Calculando Risk Score…")
        score, level = calculate_score(unique, result)

        result.findings = unique
        result.risk_score = score
        result.risk_level = level
        result.finalize()

        self._step(
            "COMPLETE",
            f"Risk Score: {score}/100 ({level.upper()}) · "
            f"{len(unique)} hallazgos únicos",
        )
        return result

    def _step(self, stage: str, message: str) -> None:
        self._progress(stage, message)
        logger.info("[%s] %s", stage, message)
