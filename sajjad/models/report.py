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
    # Plan Agency: el reporte sale con la marca del cliente en
    # vez de la de Sajjad (portada, pie de página y disclaimer).
    white_label: bool = False

    @property
    def brand_name(self) -> str:
        """
        Marca que encabeza el reporte. En modo white-label es la
        del cliente; si no hay nombre de empresa, cae a Sajjad
        para no emitir un PDF sin identificar.
        """
        if self.white_label and self.company_name:
            return self.company_name
        return "SAJJAD"

    @property
    def footer_brand(self) -> str:
        """Marca del pie de página (nombre largo del producto)."""
        if self.white_label and self.company_name:
            return self.company_name
        return "Sajjad EASM"

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
