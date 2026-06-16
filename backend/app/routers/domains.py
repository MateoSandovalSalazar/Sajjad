"""
Domain management routes.

GET    /domains              → list user's domains
POST   /domains              → add domain (plan limit enforced)
DELETE /domains/{id}         → remove domain + cascade scans
POST   /domains/{id}/verify  → trigger DNS TXT check
GET    /domains/{id}/instructions → get TXT record instructions
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.core.exceptions import Conflict, Forbidden, NotFound
from app.core.limits import get_limits
from app.dependencies import DB, VerifiedUser
from app.models.domain import Domain
from app.schemas.domain import (
    DomainCreate,
    DomainResponse,
    VerificationInstructions,
)
from app.services.domain_verifier import verify_domain_ownership

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=list[DomainResponse])
async def list_domains(user: VerifiedUser, db: DB):
    result = await db.execute(
        select(Domain)
        .where(Domain.user_id == user.id)
        .order_by(Domain.created_at)
    )
    return result.scalars().all()


@router.post("", response_model=DomainResponse, status_code=201)
async def add_domain(
    payload: DomainCreate,
    user: VerifiedUser,
    db: DB,
):
    plan = user.subscription.plan if user.subscription else "free"
    limits = get_limits(plan)

    # Count existing domains
    result = await db.execute(
        select(Domain).where(Domain.user_id == user.id)
    )
    current_count = len(result.scalars().all())

    if current_count >= limits.max_domains:
        from app.core.exceptions import PlanLimitExceeded

        raise PlanLimitExceeded(
            f"Your {plan} plan supports up to {limits.max_domains} "
            f"domain(s). Upgrade to add more."
        )

    # Check duplicate
    existing = await db.execute(
        select(Domain).where(
            Domain.user_id == user.id,
            Domain.fqdn == payload.fqdn,
        )
    )
    if existing.scalar_one_or_none():
        raise Conflict(f"Domain '{payload.fqdn}' already added.")

    domain = Domain(user_id=user.id, fqdn=payload.fqdn)
    db.add(domain)
    await db.flush()
    return domain


@router.get("/{domain_id}", response_model=DomainResponse)
async def get_domain(
    domain_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    return await _get_user_domain(domain_id, user.id, db)


@router.delete("/{domain_id}", status_code=204)
async def remove_domain(
    domain_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    domain = await _get_user_domain(domain_id, user.id, db)
    await db.delete(domain)


@router.post("/{domain_id}/verify", response_model=DomainResponse)
async def trigger_verify(
    domain_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    domain = await _get_user_domain(domain_id, user.id, db)

    await verify_domain_ownership(
        domain.fqdn, domain.verification_token
    )

    domain.verified_at = datetime.now(timezone.utc)
    await db.flush()
    return domain


@router.get(
    "/{domain_id}/instructions",
    response_model=VerificationInstructions,
)
async def get_instructions(
    domain_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    domain = await _get_user_domain(domain_id, user.id, db)
    return VerificationInstructions(
        domain=domain.fqdn,
        record_type="TXT",
        record_name=domain.fqdn,
        record_value=domain.verification_token,
        instructions=(
            f"Add a TXT DNS record to '{domain.fqdn}' with the "
            f"value '{domain.verification_token}'. "
            f"Propagation can take up to 48 hours. "
            f"Then click 'Verify' in your dashboard."
        ),
    )


async def _get_user_domain(
    domain_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DB,
) -> Domain:
    result = await db.execute(
        select(Domain).where(Domain.id == domain_id)
    )
    domain = result.scalar_one_or_none()
    if domain is None:
        raise NotFound("Domain not found.")
    if domain.user_id != user_id:
        raise Forbidden("Access denied.")
    return domain
