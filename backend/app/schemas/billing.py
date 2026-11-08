import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.limits import PlanLimits


class PlanCapabilities(BaseModel):
    """
    Capacidades de un plan, tal como las expone la API.

    El frontend las consume desde aquí en vez de reimplementar la
    tabla de límites: `core/limits.py` es la única fuente de verdad y
    no hay forma de que las dos copias se desincronicen.
    """

    max_domains: int
    max_scans_per_month: int
    scan_interval_days: int | None
    can_download_pdf: bool
    can_see_findings: bool
    white_label: bool

    @classmethod
    def from_limits(cls, limits: PlanLimits) -> "PlanCapabilities":
        return cls(
            max_domains=limits.max_domains,
            max_scans_per_month=limits.max_scans_per_month,
            scan_interval_days=limits.scan_interval_days,
            can_download_pdf=limits.can_download_pdf,
            can_see_findings=limits.can_see_findings,
            white_label=limits.white_label,
        )


class PlanInfo(BaseModel):
    name: str
    label: str
    price_usd: int
    is_trial: bool
    capabilities: PlanCapabilities

    @classmethod
    def from_limits(cls, name: str, limits: PlanLimits) -> "PlanInfo":
        return cls(
            name=name,
            label=limits.label or name.capitalize(),
            price_usd=limits.price_usd,
            is_trial=limits.is_trial,
            capabilities=PlanCapabilities.from_limits(limits),
        )


class CheckoutRequest(BaseModel):
    plan: str  # starter | professional | agency


class CheckoutResponse(BaseModel):
    checkout_url: str
    preference_id: str


class SubscriptionOut(BaseModel):
    """
    Estado de plan del usuario. `plan` es el plan EFECTIVO (un trial
    vencido reporta free aunque la fila aún no se haya degradado).
    """

    id: uuid.UUID
    plan: str
    plan_label: str
    status: str
    capabilities: PlanCapabilities
    current_period_end: datetime | None
    scans_this_month: int
    created_at: datetime

    # Prueba gratuita
    is_trial: bool = False
    trial_ends_at: datetime | None = None
    trial_days_left: int | None = None

    # Si es false, el frontend oculta el botón de mejorar plan:
    # la pasarela de pagos todavía no está activa.
    billing_enabled: bool = False
