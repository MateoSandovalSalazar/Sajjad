"""
Public / freemium routes — no authentication required.

POST /public/trial-scan → launch a free one-time scan.
                          Returns score + summary only.
                          Findings are locked behind sign-up.

Rate-limited aggressively: 1 trial per IP per 24 hours.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.core.exceptions import PlanLimitExceeded
from app.dependencies import DB
from app.schemas.scan import ScanScoreOut, ScanStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["public"])

# In-memory IP throttle — good enough for MVP.
# Replace with Redis in production.
_trial_ip_cache: dict[str, datetime] = {}
_TRIAL_COOLDOWN_HOURS = 24


@router.post("/trial-scan", response_model=ScanScoreOut)
async def trial_scan(
    request: Request,
    payload: "TrialScanRequest",
    db: DB,
):
    """
    Freemium hook: unauthenticated users can scan one domain
    and see the risk score. Findings require sign-up.
    """
    client_ip = _get_client_ip(request)
    _check_rate_limit(client_ip)

    # Validate domain format
    domain = _normalize_domain(payload.domain)

    # Import here to avoid circular at module load
    from sajjad.orchestrator import Orchestrator

    orchestrator = Orchestrator(domain=domain)
    result = orchestrator.run()

    _trial_ip_cache[client_ip] = datetime.now(timezone.utc)

    return ScanScoreOut(
        scan_id=uuid.uuid4(),
        domain=domain,
        status=ScanStatus.COMPLETED,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        findings_summary=result.summary,
        completed_at=datetime.now(timezone.utc),
        requires_plan=True,
    )


def _check_rate_limit(ip: str) -> None:
    from datetime import timedelta

    last = _trial_ip_cache.get(ip)
    if last is not None:
        elapsed = datetime.now(timezone.utc) - last
        if elapsed.total_seconds() < _TRIAL_COOLDOWN_HOURS * 3600:
            remaining = int(
                _TRIAL_COOLDOWN_HOURS * 3600
                - elapsed.total_seconds()
            )
            hours = remaining // 3600
            raise PlanLimitExceeded(
                f"Trial scan limit: one scan per {_TRIAL_COOLDOWN_HOURS}h "
                f"per IP. Try again in {hours}h or create a free account."
            )


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _normalize_domain(raw: str) -> str:
    import re

    domain = raw.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/")[0]
    if not re.match(r"^[a-z0-9][a-z0-9\-\.]{1,250}[a-z0-9]$", domain):
        raise ValueError(f"Invalid domain: {raw}")
    return domain


# Pydantic model defined here to keep the module self-contained
from pydantic import BaseModel, field_validator  # noqa: E402


class TrialScanRequest(BaseModel):
    domain: str

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        return _normalize_domain(v)
