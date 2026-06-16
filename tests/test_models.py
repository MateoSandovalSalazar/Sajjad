import pytest
from sajjad.models.finding import Finding


def _make_finding(**kwargs) -> Finding:
    defaults = dict(
        category="port",
        severity="high",
        title="Test finding",
        description="Test description",
        evidence={},
        recommendation="Fix it",
        source_tool="nmap",
        host="example.com",
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def test_finding_valid():
    f = _make_finding()
    assert f.severity == "high"
    assert f.category == "port"
    assert f.id  # UUID was generated


def test_finding_invalid_severity():
    with pytest.raises(ValueError, match="Invalid severity"):
        _make_finding(severity="extreme")


def test_finding_invalid_category():
    with pytest.raises(ValueError, match="Invalid category"):
        _make_finding(category="unknown_category")


def test_finding_fingerprint_stable():
    f1 = _make_finding(host="sub.example.com", port=3306)
    f2 = _make_finding(host="sub.example.com", port=3306)
    assert f1.fingerprint() == f2.fingerprint()


def test_finding_fingerprint_differs_by_port():
    f1 = _make_finding(host="example.com", port=3306)
    f2 = _make_finding(host="example.com", port=5432)
    assert f1.fingerprint() != f2.fingerprint()


def test_finding_severity_rank_order():
    severities = ["critical", "high", "medium", "low", "info"]
    findings = [_make_finding(severity=s) for s in severities]
    ranks = [f.severity_rank for f in findings]
    assert ranks == sorted(ranks)


def test_finding_is_actionable():
    assert _make_finding(severity="critical").is_actionable()
    assert _make_finding(severity="high").is_actionable()
    assert _make_finding(severity="medium").is_actionable()
    assert not _make_finding(severity="low").is_actionable()
    assert not _make_finding(severity="info").is_actionable()
