from dataclasses import dataclass, field
from datetime import datetime, timezone

from .scan_result import ScanResult


@dataclass
class Report:
    scan_result: ScanResult
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    company_name: str = ""
    analyst_notes: str = ""

    @property
    def domain(self) -> str:
        return self.scan_result.domain

    @property
    def risk_score(self) -> int:
        return self.scan_result.risk_score

    @property
    def risk_level(self) -> str:
        return self.scan_result.risk_level

    @property
    def scan_id(self) -> str:
        return self.scan_result.scan_id
