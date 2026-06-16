"""
Stage 4 — Port Scanning

Two-phase approach:
  1. naabu — fast SYN scan to enumerate open ports
  2. nmap  — service/version detection on discovered ports

nmap output is parsed from XML (-oX -) for completeness.
"""

import logging
import xml.etree.ElementTree as ET
from typing import Any

from sajjad.models.finding import Finding

from . import parse_jsonl, run_tool

logger = logging.getLogger(__name__)

# Ports that are dangerous when exposed to the internet
HIGH_RISK_PORTS: dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    110: "POP3",
    143: "IMAP",
    2000: "SCCP/VoIP",
    2049: "NFS",
    3306: "MySQL",
    3389: "RDP",
    5060: "SIP/VoIP",
    5061: "SIP-TLS/VoIP",
    5432: "PostgreSQL",
    5900: "VNC",
    5984: "CouchDB",
    6379: "Redis",
    6443: "Kubernetes API",
    8080: "HTTP alternativo",
    8443: "HTTPS alternativo",
    9200: "Elasticsearch",
    9300: "Elasticsearch transport",
    11211: "Memcached",
    27017: "MongoDB",
}

# SIP/VoIP ports exposed to internet enable toll fraud and enumeration
VOIP_PORTS: frozenset[int] = frozenset({5060, 5061, 2000})

DATABASE_PORTS: frozenset[int] = frozenset({
    3306, 5432, 6379, 27017, 9200,
    9300, 5984, 11211,
})


def scan_with_naabu(
    hosts: list[str],
    timeout: int = 180,
) -> list[dict[str, Any]]:
    if not hosts:
        return []

    import tempfile, os as _os
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp:
        tmp.write("\n".join(hosts))
        tmp_path = tmp.name

    try:
        cmd = [
            "naabu",
            "-hL", tmp_path,
            "-json",
            "-nC",
            "-ports", "top-1000",
            "-rate", "1000",
        ]
        output = run_tool(cmd, timeout=timeout)
        records = parse_jsonl(output)
        logger.info(
            "naabu: %d open port/host combinations", len(records)
        )
        return records
    finally:
        _os.unlink(tmp_path)


def scan_with_nmap(
    host: str,
    ports: list[int],
    timeout: int = 120,
) -> list[dict[str, Any]]:
    if not ports:
        return []

    port_list = ",".join(str(p) for p in ports)
    cmd = [
        "nmap",
        "-sV",           # service/version detection
        "--version-intensity", "5",
        "-p", port_list,
        "--open",
        "-oX", "-",
        host,
    ]
    output = run_tool(cmd, timeout=timeout)
    return _parse_nmap_xml(output, host)


def scan_ports(
    hosts: list[str],
    timeout: int = 300,
) -> dict[str, list[int]]:
    naabu_results = scan_with_naabu(hosts, timeout=timeout // 2)

    host_ports: dict[str, list[int]] = {}
    for record in naabu_results:
        host = record.get("host") or record.get("ip", "")
        port = record.get("port")
        if host and port:
            host_ports.setdefault(host, []).append(int(port))

    # nmap service detection — use full timeout, not half
    for host, ports in host_ports.items():
        try:
            services = scan_with_nmap(host, ports, timeout=timeout)
            if services:
                host_ports[host] = [s["port"] for s in services]
        except Exception as exc:
            logger.warning("nmap failed for %s: %s", host, exc)

    return host_ports


def analyze_ports(
    open_ports: dict[str, list[int]],
) -> list[Finding]:
    findings: list[Finding] = []

    for host, ports in open_ports.items():
        for port in ports:
            service = HIGH_RISK_PORTS.get(port)
            if service is None:
                continue

            if port in DATABASE_PORTS:
                findings.append(Finding(
                    category="port",
                    severity="critical",
                    title=f"Base de datos expuesta: {service} en {host}",
                    description=(
                        f"El puerto {port} ({service}) está accesible "
                        "directamente desde internet. Las bases de datos "
                        "no deberían ser accesibles públicamente."
                    ),
                    evidence={
                        "host": host,
                        "port": port,
                        "service": service,
                    },
                    recommendation=(
                        f"Restringir el acceso al puerto {port} con "
                        "firewall. Solo permitir conexiones desde IPs "
                        "de confianza o usar VPN/túnel SSH."
                    ),
                    source_tool="naabu",
                    host=host,
                    port=port,
                ))
            elif port in (3389, 5900):
                findings.append(Finding(
                    category="port",
                    severity="high",
                    title=(
                        f"Acceso remoto expuesto: "
                        f"{service} en {host}:{port}"
                    ),
                    description=(
                        f"{service} (puerto {port}) está accesible "
                        "desde internet. Esto expone la superficie "
                        "de ataque a fuerza bruta y exploits."
                    ),
                    evidence={
                        "host": host,
                        "port": port,
                        "service": service,
                    },
                    recommendation=(
                        "Restringir acceso con firewall y usar VPN "
                        "para acceso remoto. Deshabilitar si no se usa."
                    ),
                    source_tool="naabu",
                    host=host,
                    port=port,
                ))
            elif port == 23:
                findings.append(Finding(
                    category="port",
                    severity="critical",
                    title=f"Telnet expuesto en {host}:{port}",
                    description=(
                        "Telnet transmite credenciales en texto plano. "
                        "Su exposición a internet es crítica."
                    ),
                    evidence={"host": host, "port": port},
                    recommendation=(
                        "Deshabilitar Telnet inmediatamente. "
                        "Usar SSH como reemplazo seguro."
                    ),
                    source_tool="naabu",
                    host=host,
                    port=port,
                ))
            elif port in VOIP_PORTS:
                findings.append(Finding(
                    category="port",
                    severity="high",
                    title=(
                        f"Puerto VoIP expuesto a internet: "
                        f"{service} en {host}:{port}"
                    ),
                    description=(
                        f"El puerto {port} ({service}) está accesible "
                        "desde internet. Los servicios SIP/VoIP expuestos "
                        "son objetivo frecuente de fraude telefónico (toll "
                        "fraud), enumeración de extensiones y ataques de "
                        "fuerza bruta sobre credenciales SIP."
                    ),
                    evidence={
                        "host": host,
                        "port": port,
                        "service": service,
                    },
                    recommendation=(
                        "Restringir el acceso al puerto SIP/VoIP con "
                        "firewall. Permitir solo IPs de proveedores VoIP "
                        "conocidos. Habilitar fail2ban o equivalente "
                        "para bloquear intentos de enumeración."
                    ),
                    source_tool="naabu",
                    host=host,
                    port=port,
                ))
            else:
                findings.append(Finding(
                    category="port",
                    severity="medium",
                    title=(
                        f"Puerto sensible expuesto: "
                        f"{service} en {host}:{port}"
                    ),
                    description=(
                        f"El servicio {service} en el puerto {port} "
                        "está accesible desde internet."
                    ),
                    evidence={
                        "host": host,
                        "port": port,
                        "service": service,
                    },
                    recommendation=(
                        "Evaluar si este servicio necesita ser "
                        "accesible públicamente. Restringir con "
                        "firewall si no es requerido."
                    ),
                    source_tool="naabu",
                    host=host,
                    port=port,
                ))

    logger.info("Port analysis: %d findings", len(findings))
    return findings


def _parse_nmap_xml(
    xml_output: str,
    host: str,
) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    if not xml_output.strip():
        return services

    try:
        root = ET.fromstring(xml_output)
        for port_el in root.iter("port"):
            state_el = port_el.find("state")
            if state_el is None:
                continue
            if state_el.get("state") != "open":
                continue

            service_el = port_el.find("service")
            services.append({
                "host": host,
                "port": int(port_el.get("portid", 0)),
                "protocol": port_el.get("protocol", "tcp"),
                "service": (
                    service_el.get("name", "unknown")
                    if service_el is not None
                    else "unknown"
                ),
                "version": (
                    service_el.get("version", "")
                    if service_el is not None
                    else ""
                ),
                "product": (
                    service_el.get("product", "")
                    if service_el is not None
                    else ""
                ),
            })
    except ET.ParseError as exc:
        logger.warning("Failed to parse nmap XML for %s: %s", host, exc)

    return services
