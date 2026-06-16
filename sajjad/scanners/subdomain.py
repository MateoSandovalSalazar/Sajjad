"""
Stage 1 — Subdomain Discovery

Combines subfinder (passive multi-source enumeration) with
crt.sh (Certificate Transparency logs) to maximize coverage.
"""

import json
import logging
from urllib.error import URLError
from urllib.request import urlopen

from . import parse_jsonl, run_tool

logger = logging.getLogger(__name__)


def run_subfinder(domain: str, timeout: int = 300) -> list[str]:
    cmd = ["subfinder", "-d", domain, "-silent", "-json"]
    output = run_tool(cmd, timeout=timeout)
    records = parse_jsonl(output)
    hosts = [r["host"] for r in records if "host" in r]
    logger.info(
        "subfinder: %d subdomains found for %s", len(hosts), domain
    )
    return hosts


def run_crtsh(domain: str) -> list[str]:
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    try:
        with urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except (URLError, json.JSONDecodeError, Exception) as exc:
        logger.warning("crt.sh query failed for %s: %s", domain, exc)
        return []

    names: set[str] = set()
    for entry in data:
        for name in entry.get("name_value", "").splitlines():
            clean = name.strip().lstrip("*.")
            if clean.endswith(f".{domain}") or clean == domain:
                names.add(clean)

    logger.info(
        "crt.sh: %d subdomains found for %s", len(names), domain
    )
    return list(names)


def discover_subdomains(
    domain: str,
    timeout: int = 300,
) -> list[str]:
    sf = run_subfinder(domain, timeout=timeout)
    ct = run_crtsh(domain)
    combined = sorted(set(sf) | set(ct))
    logger.info(
        "Subdomain discovery complete for %s: %d unique",
        domain,
        len(combined),
    )
    return combined
