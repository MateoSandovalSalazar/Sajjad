import secrets
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _gen_token() -> str:
    return f"sajjad-verify-{secrets.token_hex(8)}"


class Domain(Base):
    __tablename__ = "domains"
    __table_args__ = (
        UniqueConstraint("user_id", "fqdn", name="uq_user_domain"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fqdn: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    verification_token: Mapped[str] = mapped_column(
        String(64), nullable=False, default=_gen_token
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Registro de autorización ─────────────────────────────
    #
    # Sajjad escanea infraestructura ajena: la defensa legal es poder
    # demostrar que el titular de la cuenta declaró ser dueño del
    # dominio y autorizó el escaneo. Se guarda cuándo, desde qué IP y
    # con qué navegador — un checkbox sin rastro no prueba nada.
    #
    # La verificación DNS TXT demuestra el control técnico; esto
    # documenta el consentimiento explícito. Hacen falta las dos.
    authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    authorized_ip: Mapped[str | None] = mapped_column(
        String(45), nullable=True  # 45 = IPv6 en su forma más larga
    )
    authorized_user_agent: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="domains")  # noqa: F821
    scans: Mapped[list["Scan"]] = relationship(  # noqa: F821
        back_populates="domain",
        cascade="all, delete-orphan",
    )

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None
