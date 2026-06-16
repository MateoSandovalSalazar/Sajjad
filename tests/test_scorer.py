import pytest
from sajjad.analysis.scorer import calculate_score, _risk_level
from sajjad.models.finding import Finding
from sajjad.models.scan_result import ScanResult


def _finding(severity: str, category: str = "vuln") -> Finding:
    return Finding(
        category=category,
        severity=severity,
        title=f"{severity} finding",
        description="desc",
        evidence={},
        recommendation="fix",
        source_tool="test",
        host="example.com",
    )


def _result(domain: str = "example.com") -> ScanResult:
    return ScanResult(domain=domain)


def test_empty_findings_score_zero():
    score, level = calculate_score([], _result())
    assert score == 0
    assert level == "low"


def test_single_critical_finding():
    score, level = calculate_score(
        [_finding("critical")], _result()
    )
    # 1 critical = 25 pts → "low" per spec (0-25 = Low)
    assert score == 25
    assert level == "low"


def test_two_critical_findings_reach_medium():
    score, level = calculate_score(
        [_finding("critical"), _finding("critical")], _result()
    )
    # 2 critical = 50 pts → "medium" (26-50)
    assert score == 50
    assert level == "medium"


def test_score_capped_at_100():
    findings = [_finding("critical")] * 20
    score, _ = calculate_score(findings, _result())
    assert score <= 100


def test_credential_breach_multiplier():
    base_findings = [_finding("medium")]
    result = _result()
    score_without, _ = calculate_score(base_findings, result)

    with_cred = base_findings + [_finding("critical", category="cred")]
    score_with, _ = calculate_score(with_cred, result)
    assert score_with > score_without


def test_risk_level_thresholds():
    assert _risk_level(0) == "low"
    assert _risk_level(25) == "low"
    assert _risk_level(26) == "medium"
    assert _risk_level(50) == "medium"
    assert _risk_level(51) == "high"
    assert _risk_level(75) == "high"
    assert _risk_level(76) == "critical"
    assert _risk_level(100) == "critical"


def test_many_subdomains_bonus():
    result = _result()
    result.subdomains = [f"sub{i}.example.com" for i in range(15)]
    score, _ = calculate_score([_finding("low")], result)
    # Bonus of 5 for >10 subdomains should be applied
    assert score >= 6  # 1 (low) + 5 (bonus)
