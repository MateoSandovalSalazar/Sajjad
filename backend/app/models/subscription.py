import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.limits import FREE_PLAN, TRIAL_PLAN
from app.database import Base


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    plan: Mapped[str] = mapped_column(
        String(32), nullable=False, default="free"
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(
            SubscriptionStatus,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    mp_subscription_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True
    )
    mp_payer_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    mp_preapproval_plan_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Fin de la prueba gratuita. Sólo relevante cuando plan="trial";
    # al pasar esta fecha, el beat diario degrada la cuenta a free.
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scans_this_month: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    scans_reset_at: Mapped[datetime | None] = mapped_column(
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
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscription")  # noqa: F821

    @property
    def is_active(self) -> bool:
        return self.status == SubscriptionStatus.ACTIVE

    @property
    def is_trial(self) -> bool:
        return self.plan == TRIAL_PLAN

    def trial_days_left(self, now: datetime | None = None) -> int | None:
        """
        Días enteros restantes de prueba, o None si no está en trial.
        Nunca negativo: 0 significa que ya expiró.
        """
        if not self.is_trial or self.trial_ends_at is None:
            return None
        now = now or datetime.now(timezone.utc)
        remaining = self.trial_ends_at - now
        return max(0, remaining.days + (1 if remaining.seconds else 0))

    def is_trial_expired(self, now: datetime | None = None) -> bool:
        if not self.is_trial or self.trial_ends_at is None:
            return False
        return (now or datetime.now(timezone.utc)) >= self.trial_ends_at

    @property
    def effective_plan(self) -> str:
        """
        Plan realmente vigente en este instante.

        Una suscripción cancelada, o un trial cuya fecha ya pasó,
        valen free aunque la columna `plan` aún diga otra cosa: el
        beat que degrada corre una vez al día y no queremos regalar
        hasta 24 h de capacidades de pago en esa ventana.
        """
        if not self.is_active or self.is_trial_expired():
            return FREE_PLAN
        return self.plan
