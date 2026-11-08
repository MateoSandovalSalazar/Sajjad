import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .finding import Finding


@dataclass
class ScanResult:
    domain: str
    scan_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None
    subdomains: list[str] = field(default_factory=list)
    live_hosts: list[str] = field(default_factory=list)
    open_ports: dict[str, list[int]] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    risk_score: int = 0
    risk_level: str = "low"
    summary: dict[str, int] = field(default_factory=dict)

    def finalize(self) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.summary = self._build_summary()

    def _build_summary(self) -> dict[str, int]:
        counts: dict[str, int] = {
            s: 0 for s in ("critical", "high", "medium", "low", "info")
        }
        for f in self.findings:
            counts[f.severity] += 1
        return counts

    @property
    def duration_seconds(self) -> float | None:
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def findings_by_severity(self) -> dict[str, list[Finding]]:
        grouped: dict[str, list[Finding]] = {
            s: [] for s in ("critical", "high", "medium", "low", "info")
        }
        for f in sorted(self.findings, key=lambda x: x.severity_rank):
            grouped[f.severity].append(f)
        return grouped

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def total_open_ports(self) -> int:
        return sum(len(ps) for ps in self.open_ports.values())
