import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    status: Mapped[ScanStatus] = mapped_column(
        Enum(
            ScanStatus,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ScanStatus.PENDING,
        index=True,
    )
    progress_stage: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    risk_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    risk_level: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    subdomains_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    live_hosts_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    open_ports_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    findings_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    findings_summary: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    raw_data: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    pdf_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    domain: Mapped["Domain"] = relationship(back_populates="scans")  # noqa: F821
    user: Mapped["User"] = relationship(back_populates="scans")  # noqa: F821
    findings: Mapped[list["Finding"]] = relationship(  # noqa: F821
        back_populates="scan",
        cascade="all, delete-orphan",
        order_by="Finding.severity_rank",
    )

    @property
    def is_terminal(self) -> bool:
        return self.status in (ScanStatus.COMPLETED, ScanStatus.FAILED)


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )
    severity_rank: Mapped[int] = mapped_column(
        Integer, nullable=False, default=4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    source_tool: Mapped[str] = mapped_column(String(64), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cve: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cvss_score: Mapped[float | None] = mapped_column(
        nullable=True
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    scan: Mapped["Scan"] = relationship(back_populates="findings")
