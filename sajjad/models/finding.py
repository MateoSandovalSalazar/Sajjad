from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

VALID_CATEGORIES = frozenset({
    "subdomain", "port", "cert", "cred",
    "dns", "vuln", "cloud", "osint",
})

VALID_SEVERITIES = frozenset({
    "critical", "high", "medium", "low", "info",
})

SEVERITY_RANK: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}


@dataclass
class Finding:
    category: str
    severity: str
    title: str
    description: str
    evidence: dict[str, Any]
    recommendation: str
    source_tool: str
    host: str
    id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    cvss_score: float | None = None
    cve: str | None = None
    port: int | None = None
    discovered_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category: {self.category!r}. "
                f"Valid: {sorted(VALID_CATEGORIES)}"
            )
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity: {self.severity!r}. "
                f"Valid: {sorted(VALID_SEVERITIES)}"
            )

    @property
    def severity_rank(self) -> int:
        return SEVERITY_RANK[self.severity]

    def is_actionable(self) -> bool:
        return self.severity in ("critical", "high", "medium")

    def fingerprint(self) -> str:
        """Stable key used for deduplication."""
        parts = [
            self.category,
            self.severity,
            self.host,
            str(self.port or ""),
            self.title[:60],
        ]
        return "|".join(parts).lower()
