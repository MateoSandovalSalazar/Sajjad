from sajjad.analysis.deduplicator import deduplicate, _jaccard
from sajjad.models.finding import Finding


def _finding(
    title: str,
    host: str = "example.com",
    severity: str = "medium",
    category: str = "vuln",
    port: int | None = None,
) -> Finding:
    return Finding(
        category=category,
        severity=severity,
        title=title,
        description="desc",
        evidence={},
        recommendation="fix",
        source_tool="test",
        host=host,
        port=port,
    )


def test_no_duplicates_unchanged():
    findings = [
        _finding("Issue A", host="a.example.com"),
        _finding("Issue B", host="b.example.com"),
        _finding("Issue C", host="c.example.com"),
    ]
    result = deduplicate(findings)
    assert len(result) == 3


def test_exact_duplicates_removed():
    f1 = _finding("Same issue", host="example.com", port=80)
    f2 = _finding("Same issue", host="example.com", port=80)
    result = deduplicate([f1, f2])
    assert len(result) == 1


def test_higher_severity_kept_on_exact_dup():
    low = _finding("Issue X", severity="low")
    critical = _finding("Issue X", severity="critical")
    result = deduplicate([low, critical])
    assert len(result) == 1
    assert result[0].severity == "critical"


def test_different_ports_not_deduped():
    f1 = _finding("DB exposed", port=3306)
    f2 = _finding("DB exposed", port=5432)
    result = deduplicate([f1, f2])
    assert len(result) == 2


def test_different_hosts_not_deduped():
    f1 = _finding("Issue", host="a.example.com")
    f2 = _finding("Issue", host="b.example.com")
    result = deduplicate([f1, f2])
    assert len(result) == 2


def test_jaccard_identical():
    assert _jaccard("hello world", "hello world") == 1.0


def test_jaccard_disjoint():
    assert _jaccard("hello world", "foo bar") == 0.0


def test_jaccard_partial():
    score = _jaccard("hello world test", "hello world")
    assert 0.0 < score < 1.0


def test_empty_input():
    assert deduplicate([]) == []
