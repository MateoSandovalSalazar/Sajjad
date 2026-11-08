"""
Plan limits and enforcement rules.

Every constraint is defined here as a single source of truth.
The dependency layer enforces these at request time.
"""

from dataclasses import dataclass
from datetime import datetime


def is_new_billing_month(
    reset_at: datetime | None, now: datetime
) -> bool:
    """
    True si el contador mensual de escaneos debe reiniciarse: nunca
    se reinició, o cambiamos de mes calendario desde el último reset.
    """
    if reset_at is None:
        return True
    return (reset_at.year, reset_at.month) != (now.year, now.month)


@dataclass(frozen=True)
class PlanLimits:
    max_domains: int
    max_scans_per_month: int
    scan_interval_days: int | None   # None = manual only
    can_download_pdf: bool
    can_see_findings: bool
    white_label: bool
    price_usd: int
    label: str = ""
    # Plan de cortesía y por tiempo limitado: no se vende ni se
    # muestra en la grilla de precios.
    is_trial: bool = False


PLANS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        max_domains=1,
        max_scans_per_month=1,
        scan_interval_days=None,
        can_download_pdf=False,
        can_see_findings=False,
        white_label=False,
        price_usd=0,
        label="Free",
    ),
    # Prueba gratuita: capacidades de Professional durante
    # settings.trial_days. Al expirar cae a free automáticamente.
    "trial": PlanLimits(
        max_domains=3,
        max_scans_per_month=10,
        scan_interval_days=1,
        can_download_pdf=True,
        can_see_findings=True,
        white_label=False,
        price_usd=0,
        label="Prueba gratuita",
        is_trial=True,
    ),
    "starter": PlanLimits(
        max_domains=1,
        max_scans_per_month=4,
        scan_interval_days=7,
        can_download_pdf=True,
        can_see_findings=True,
        white_label=False,
        price_usd=30,
        label="Starter",
    ),
    "professional": PlanLimits(
        max_domains=3,
        max_scans_per_month=30,
        scan_interval_days=1,
        can_download_pdf=True,
        can_see_findings=True,
        white_label=False,
        price_usd=50,
        label="Professional",
    ),
    "agency": PlanLimits(
        max_domains=10,
        max_scans_per_month=300,
        scan_interval_days=1,
        can_download_pdf=True,
        can_see_findings=True,
        white_label=True,
        price_usd=120,
        label="Agency",
    ),
}

# Planes que se cobran. Todo lo demás (free, trial) se otorga.
PAID_PLANS: tuple[str, ...] = ("starter", "professional", "agency")

TRIAL_PLAN = "trial"
FREE_PLAN = "free"


def get_limits(plan: str) -> PlanLimits:
    return PLANS.get(plan, PLANS[FREE_PLAN])
