"""
Risk Score Calculation

Produces a 0-100 score from findings and scan metadata.
Score composition:
  - Base points per finding severity (capped at 80)
  - Fixed bonuses for structural weaknesses (up to 20)
  - Multiplier for active credential exposure
"""

import logging

from sajjad.models.finding import Finding
from sajjad.models.scan_result import ScanResult

logger = logging.getLogger(__name__)

SEVERITY_POINTS: dict[str, int] = {
    "critical": 25,
    "high": 10,
    "medium": 3,
    "low": 1,
    "info": 0,
}

RISK_THRESHOLDS: list[tuple[int, str]] = [
    (76, "critical"),
    (51, "high"),
    (26, "medium"),
    (0, "low"),
]


def calculate_score(
    findings: list[Finding],
    result: ScanResult,
) -> tuple[int, str]:
    base = _base_score(findings)
    bonuses = _structural_bonuses(findings, result)

    raw = base + bonuses

    if _has_active_credentials(findings):
        raw = int(raw * 1.5)

    score = min(100, max(0, raw))
    level = _risk_level(score)

    logger.info(
        "Risk Score: %d (%s) — base=%d bonuses=%d",
        score, level, base, bonuses,
    )
    return score, level


def _base_score(findings: list[Finding]) -> int:
    total = 0
    for f in findings:
        total += SEVERITY_POINTS[f.severity]
    return min(80, total)


def _structural_bonuses(
    findings: list[Finding],
    result: ScanResult,
) -> int:
    bonus = 0

    if _has_expired_certificate(findings):
        bonus += 15

    if _has_exposed_database(findings):
        bonus += 20

    if len(result.subdomains) > 10:
        bonus += 5

    if _missing_email_protection(findings):
        bonus += 8

    return bonus


def _has_active_credentials(findings: list[Finding]) -> bool:
    return any(f.category == "cred" for f in findings)


def _has_expired_certificate(findings: list[Finding]) -> bool:
    return any(
        f.category == "cert" and "vencido" in f.title.lower()
        for f in findings
    )


def _has_exposed_database(findings: list[Finding]) -> bool:
    return any(
        f.category == "port"
        and f.severity == "critical"
        for f in findings
    )


def _missing_email_protection(findings: list[Finding]) -> bool:
    has_spf_issue = any(
        f.category == "dns" and "spf" in f.title.lower()
        for f in findings
    )
    has_dmarc_issue = any(
        f.category == "dns" and "dmarc" in f.title.lower()
        for f in findings
    )
    return has_spf_issue or has_dmarc_issue


def _risk_level(score: int) -> str:
    for threshold, level in RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"
