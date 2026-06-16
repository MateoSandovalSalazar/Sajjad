"""
Stage 7 — Vulnerability Detection

Runs nuclei with community templates scoped to safe detection
tags only. DoS, fuzzing, and intrusive tags are always excluded.

Nuclei severity levels are mapped to Sajjad's severity model.
"""

import logging
import os
import tempfile
from typing import Any

from sajjad.models.finding import Finding

from . import parse_jsonl, run_tool

logger = logging.getLogger(__name__)

# Map nuclei severity to Sajjad severity
SEVERITY_MAP: dict[str, str] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "info",
    "unknown": "info",
}

# Always excluded — never run destructive checks
EXCLUDED_TAGS = "dos,fuzz,intrusive,bruteforce,crawl"


def scan_vulnerabilities(
    urls: list[str],
    timeout: int = 600,
    rate_limit: int = 150,
) -> list[Finding]:
    if not urls:
        return []

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as tmp:
        tmp.write("\n".join(urls))
        tmp_path = tmp.name

    try:
        cmd = [
            "nuclei",
            "-l", tmp_path,
            "-severity", "critical,high,medium,low",
            "-j",        # -jsonl: JSONL output to stdout (nuclei v3)
            "-silent",
            "-exclude-tags", EXCLUDED_TAGS,
            "-rate-limit", str(rate_limit),
            "-timeout", "10",
        ]
        output = run_tool(cmd, timeout=timeout)
        records = parse_jsonl(output)
        findings = [_record_to_finding(r) for r in records]
        valid = [f for f in findings if f is not None]
        logger.info(
            "nuclei: %d vulnerabilities detected across %d targets",
            len(valid),
            len(urls),
        )
        return valid  # type: ignore[return-value]
    finally:
        os.unlink(tmp_path)


def _record_to_finding(
    record: dict[str, Any],
) -> Finding | None:
    try:
        info = record.get("info", {})
        raw_severity = info.get("severity", "info").lower()
        severity = SEVERITY_MAP.get(raw_severity, "info")

        host = record.get("host", "")
        matched_at = record.get("matched-at", host)
        template_id = record.get("template-id", "unknown")
        name = info.get("name", template_id)
        description = info.get("description", "")
        remediation = (
            info.get("remediation")
            or "Revisar la documentación del template nuclei "
            f"({template_id}) para instrucciones de remediación."
        )
        references = info.get("reference", [])
        cve = _extract_cve(info)

        return Finding(
            category="vuln",
            severity=severity,
            title=f"{name}: {host}",
            description=description or (
                f"Vulnerabilidad detectada por nuclei "
                f"(template: {template_id}) en {matched_at}."
            ),
            evidence={
                "template_id": template_id,
                "matched_at": matched_at,
                "matcher_name": record.get("matcher-name", ""),
                "type": record.get("type", ""),
                "references": references,
            },
            recommendation=remediation,
            source_tool="nuclei",
            host=host,
            cve=cve,
        )
    except (KeyError, ValueError) as exc:
        logger.warning(
            "Failed to parse nuclei record: %s — %s", record, exc
        )
        return None


def _extract_cve(info: dict[str, Any]) -> str | None:
    classification = info.get("classification", {})
    cve_ids = classification.get("cve-id", [])
    if isinstance(cve_ids, list) and cve_ids:
        return cve_ids[0]
    if isinstance(cve_ids, str) and cve_ids:
        return cve_ids
    return None
