import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.limits import FREE_PLAN, PlanLimits, get_limits
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default=""
    )
    company: Mapped[str] = mapped_column(
        String(255), nullable=False, default=""
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    email_verification_token: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    password_reset_token: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    password_reset_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Se incrementa al cambiar la contraseña. Va dentro del JWT (`tv`)
    # y se compara en cada petición: subirlo invalida de golpe todas
    # las sesiones abiertas de ese usuario.
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Relationships
    domains: Mapped[list["Domain"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    scans: Mapped[list["Scan"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription | None"] = relationship(  # noqa: F821
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def plan(self) -> str:
        """
        Plan vigente del usuario — el único lugar del que leerlo.

        Requiere que `subscription` esté cargada (get_current_user usa
        selectinload); nunca leer `subscription.plan` directamente en
        routers, porque se salta la expiración del trial.
        """
        if self.subscription is None:
            return FREE_PLAN
        return self.subscription.effective_plan

    @property
    def limits(self) -> PlanLimits:
        return get_limits(self.plan)
