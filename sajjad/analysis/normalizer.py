"""
Finding Normalization

Post-processing step that sanitizes finding data:
  - Truncates oversized evidence blobs
  - Ensures all string fields are stripped
  - Validates severity consistency
"""

import logging

from sajjad.models.finding import Finding, VALID_SEVERITIES

logger = logging.getLogger(__name__)

MAX_DESCRIPTION_LEN = 2000
MAX_EVIDENCE_STR_LEN = 500


def normalize(findings: list[Finding]) -> list[Finding]:
    normalized = [_normalize_one(f) for f in findings]
    logger.debug("Normalized %d findings", len(normalized))
    return normalized


def _normalize_one(f: Finding) -> Finding:
    f.title = f.title.strip()[:200]
    f.description = f.description.strip()[:MAX_DESCRIPTION_LEN]
    f.recommendation = f.recommendation.strip()[:1000]
    f.host = f.host.strip().lower()
    f.evidence = _sanitize_evidence(f.evidence)

    if f.severity not in VALID_SEVERITIES:
        logger.warning(
            "Unknown severity %r on finding %s — defaulting to info",
            f.severity,
            f.id,
        )
        f.severity = "info"

    return f


def _sanitize_evidence(evidence: dict) -> dict:
    sanitized: dict = {}
    for key, value in evidence.items():
        if isinstance(value, str) and len(value) > MAX_EVIDENCE_STR_LEN:
            sanitized[key] = value[:MAX_EVIDENCE_STR_LEN] + "…"
        elif isinstance(value, list):
            sanitized[key] = value[:50]
        else:
            sanitized[key] = value
    return sanitized
