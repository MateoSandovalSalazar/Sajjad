"""
Domain management routes.

GET    /domains              → list user's domains
POST   /domains              → add domain (plan limit enforced)
DELETE /domains/{id}         → remove domain + cascade scans
POST   /domains/{id}/verify  → trigger DNS TXT check
GET    /domains/{id}/instructions → get TXT record instructions
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.core.exceptions import Conflict, NotFound
from app.core.limits import get_limits
from app.dependencies import DB, VerifiedUser
from app.models.domain import Domain
from app.schemas.domain import (
    DomainCreate,
    DomainResponse,
    VerificationInstructions,
)
from app.services.domain_verifier import verify_domain_ownership

logger = logging.getLogger(__name__)

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
    request: Request,
    payload: DomainCreate,
    user: VerifiedUser,
    db: DB,
):
    plan = user.plan
    limits = get_limits(plan)

    # COUNT en la BD: traer todas las filas sólo para medirlas carga
    # datos que no se usan.
    current_count = await db.scalar(
        select(func.count())
        .select_from(Domain)
        .where(Domain.user_id == user.id)
    )

    if (current_count or 0) >= limits.max_domains:
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

    # El schema ya obliga a payload.authorized=True; aquí se deja
    # constancia de quién lo declaró, cuándo y desde dónde.
    domain = Domain(
        user_id=user.id,
        fqdn=payload.fqdn,
        authorized_at=datetime.now(timezone.utc),
        authorized_ip=(
            request.client.host if request.client else None
        ),
        authorized_user_agent=(
            request.headers.get("user-agent", "")[:512] or None
        ),
    )
    db.add(domain)
    logger.info(
        "Autorización de escaneo registrada: user=%s dominio=%s ip=%s",
        user.id,
        payload.fqdn,
        request.client.host if request.client else "desconocida",
    )
    # Commit explícito: garantiza que el dominio quede persistido y
    # visible antes de responder. (El código tras `yield` en get_db
    # corre después de enviar la respuesta, así que un commit allí
    # llegaría tarde para una lectura inmediata del cliente.)
    await db.commit()
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
    await db.commit()


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
    await db.commit()
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
        fqdn=domain.fqdn,
        verification_token=domain.verification_token,
        dns_record_type="TXT",
        dns_record_name=domain.fqdn,
        dns_record_value=domain.verification_token,
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
    # Mismo 404 para "no existe" y "no es tuyo": un 403 confirmaría que
    # ese id existe y permitiría enumerar los dominios de otros.
    if domain is None or domain.user_id != user_id:
        raise NotFound("Domain not found.")
    return domain
