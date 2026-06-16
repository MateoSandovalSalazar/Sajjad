"""
Plan limits and enforcement rules.

Every constraint is defined here as a single source of truth.
The dependency layer enforces these at request time.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanLimits:
    max_domains: int
    max_scans_per_month: int
    scan_interval_days: int | None   # None = manual only
    can_download_pdf: bool
    can_see_findings: bool
    white_label: bool
    price_usd: int


PLANS: dict[str, PlanLimits] = {
    "free": PlanLimits(
        max_domains=1,
        max_scans_per_month=1,
        scan_interval_days=None,
        can_download_pdf=False,
        can_see_findings=False,
        white_label=False,
        price_usd=0,
    ),
    "starter": PlanLimits(
        max_domains=1,
        max_scans_per_month=4,
        scan_interval_days=7,
        can_download_pdf=True,
        can_see_findings=True,
        white_label=False,
        price_usd=30,
    ),
    "professional": PlanLimits(
        max_domains=3,
        max_scans_per_month=30,
        scan_interval_days=1,
        can_download_pdf=True,
        can_see_findings=True,
        white_label=False,
        price_usd=50,
    ),
    "agency": PlanLimits(
        max_domains=10,
        max_scans_per_month=300,
        scan_interval_days=1,
        can_download_pdf=True,
        can_see_findings=True,
        white_label=True,
        price_usd=120,
    ),
}


def get_limits(plan: str) -> PlanLimits:
    return PLANS.get(plan, PLANS["free"])


MP_PLAN_PRICES = {
    "starter": 30,
    "professional": 50,
    "agency": 120,
}
