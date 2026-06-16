"""
Finding Deduplication

Two passes:
  1. Exact — identical fingerprints (same host/port/category/title)
  2. Fuzzy — same host + category with highly similar titles

When duplicates are found, the highest-severity instance is kept.
"""

import logging

from sajjad.models.finding import Finding, SEVERITY_RANK

logger = logging.getLogger(__name__)


def deduplicate(findings: list[Finding]) -> list[Finding]:
    after_exact = _exact_dedup(findings)
    after_fuzzy = _fuzzy_dedup(after_exact)

    removed = len(findings) - len(after_fuzzy)
    if removed:
        logger.info(
            "Deduplication removed %d duplicate findings", removed
        )

    return after_fuzzy


def _exact_dedup(findings: list[Finding]) -> list[Finding]:
    seen: dict[str, Finding] = {}

    for f in findings:
        key = f.fingerprint()
        existing = seen.get(key)
        if existing is None:
            seen[key] = f
        elif SEVERITY_RANK[f.severity] < SEVERITY_RANK[existing.severity]:
            seen[key] = f

    return list(seen.values())


def _fuzzy_dedup(findings: list[Finding]) -> list[Finding]:
    """
    Collapses findings that share host+category and whose
    titles are more than 80% similar (Jaccard on word sets).
    """
    groups: list[list[Finding]] = []

    for f in findings:
        merged = False
        for group in groups:
            if _same_group(f, group[0]):
                group.append(f)
                merged = True
                break
        if not merged:
            groups.append([f])

    result: list[Finding] = []
    for group in groups:
        best = min(group, key=lambda x: SEVERITY_RANK[x.severity])
        result.append(best)

    return result


def _same_group(a: Finding, b: Finding) -> bool:
    if a.host != b.host or a.category != b.category:
        return False
    if a.port != b.port:
        return False
    return _jaccard(a.title, b.title) >= 0.80


def _jaccard(s1: str, s2: str) -> float:
    w1 = set(s1.lower().split())
    w2 = set(s2.lower().split())
    if not w1 and not w2:
        return 1.0
    union = w1 | w2
    if not union:
        return 0.0
    return len(w1 & w2) / len(union)
