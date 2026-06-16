import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.scan import ScanStatus


class ScanCreate(BaseModel):
    domain_id: uuid.UUID


class FindingOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    category: str
    severity: str
    title: str
    description: str
    recommendation: str
    source_tool: str
    host: str
    port: int | None
    cve: str | None
    cvss_score: float | None
    discovered_at: datetime


class ScanOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    domain_id: uuid.UUID
    status: ScanStatus
    progress_stage: str | None
    risk_score: int | None
    risk_level: str | None
    subdomains_count: int
    live_hosts_count: int
    open_ports_count: int
    findings_count: int
    findings_summary: dict | None
    started_at: datetime
    completed_at: datetime | None


class ScanScoreOut(BaseModel):
    """Public endpoint — score only, no findings detail."""

    scan_id: uuid.UUID
    domain: str
    status: ScanStatus
    risk_score: int | None
    risk_level: str | None
    findings_summary: dict | None
    completed_at: datetime | None
    requires_plan: bool = True


class ScanWithFindings(ScanOut):
    findings: list[FindingOut] = []


class ScanSSEEvent(BaseModel):
    """Payload emitted over Server-Sent Events."""

    scan_id: str
    status: str
    stage: str | None
    risk_score: int | None
    risk_level: str | None
    findings_count: int
