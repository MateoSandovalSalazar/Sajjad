"""
Scan management routes.

POST /scans                        → launch scan (plan-checked)
GET  /scans/{id}                   → scan status + metadata
GET  /scans/{id}/findings          → full findings (paid plans)
GET  /scans/{id}/score             → score only (free plan)
GET  /scans/{id}/stream            → SSE live progress
GET  /scans/{id}/pdf               → download PDF report (paid)
GET  /domains/{domain_id}/scans    → scan history for a domain
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core import ratelimit as rl
from app.core.exceptions import (
    Forbidden,
    NotFound,
    PlanLimitExceeded,
    ScanAlreadyRunning,
)
from app.core.limits import get_limits, is_new_billing_month
from app.core.ratelimit import limiter
from app.dependencies import DB, VerifiedUser
from app.models.domain import Domain
from app.models.scan import Scan, ScanStatus
from app.schemas.scan import (
    ScanCreate,
    ScanOut,
    ScanScoreOut,
    ScanWithFindings,
)
from app.workers.scan_task import run_scan

router = APIRouter(tags=["scans"])


@router.post("/scans", response_model=ScanOut, status_code=202)
@limiter.limit(rl.SCAN_LAUNCH)
async def launch_scan(
    request: Request,
    payload: ScanCreate,
    user: VerifiedUser,
    db: DB,
):
    domain = await _get_verified_domain(
        payload.domain_id, user.id, db
    )

    # Enforce plan limits
    plan = user.plan
    limits = get_limits(plan)

    sub = user.subscription
    # Reset mensual perezoso: si cambiamos de mes desde el último reset,
    # el contador vuelve a 0 antes de validar el límite. (No depende de
    # que un job programado corra en un momento exacto.)
    if sub and is_new_billing_month(
        sub.scans_reset_at, datetime.now(timezone.utc)
    ):
        sub.scans_this_month = 0
        sub.scans_reset_at = datetime.now(timezone.utc)

    if sub and sub.scans_this_month >= limits.max_scans_per_month:
        raise PlanLimitExceeded(
            f"Monthly scan limit reached ({limits.max_scans_per_month}). "
            f"Resets next month or upgrade your plan."
        )

    # No concurrent scans on same domain
    running = await db.execute(
        select(Scan).where(
            Scan.domain_id == domain.id,
            Scan.status.in_(
                [ScanStatus.PENDING, ScanStatus.RUNNING]
            ),
        )
    )
    if running.scalar_one_or_none():
        raise ScanAlreadyRunning(
            f"A scan is already running for '{domain.fqdn}'."
        )

    scan = Scan(domain_id=domain.id, user_id=user.id)
    db.add(scan)
    # Persistimos el scan (con su id) ANTES de encolar la tarea: el worker
    # lee el scan por id, así que debe existir en la BD antes de lanzarlo.
    await db.commit()

    task = run_scan.delay(str(scan.id))
    scan.celery_task_id = task.id
    await db.commit()

    return scan


@router.get(
    "/scans/{scan_id}",
    response_model=ScanOut,
)
async def get_scan(
    scan_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    return await _get_user_scan(scan_id, user.id, db)


@router.get(
    "/scans/{scan_id}/score",
    response_model=ScanScoreOut,
)
async def get_scan_score(
    scan_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    """
    Public-ish endpoint: returns score and summary.
    Available on free plan. Findings are withheld.
    """
    scan = await _get_user_scan(scan_id, user.id, db)
    plan = user.plan
    limits = get_limits(plan)

    domain_result = await db.execute(
        select(Domain).where(Domain.id == scan.domain_id)
    )
    domain = domain_result.scalar_one_or_none()

    return ScanScoreOut(
        scan_id=scan.id,
        domain=domain.fqdn if domain else "",
        status=scan.status,
        risk_score=scan.risk_score,
        risk_level=scan.risk_level,
        findings_summary=scan.findings_summary,
        completed_at=scan.completed_at,
        requires_plan=not limits.can_see_findings,
    )


@router.get(
    "/scans/{scan_id}/findings",
    response_model=ScanWithFindings,
)
async def get_scan_findings(
    scan_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    plan = user.plan
    if not get_limits(plan).can_see_findings:
        raise PlanLimitExceeded(
            "Detailed findings are not available on the free plan. "
            "Upgrade to Starter or higher."
        )

    result = await db.execute(
        select(Scan)
        .where(Scan.id == scan_id, Scan.user_id == user.id)
        .options(selectinload(Scan.findings))
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise NotFound("Scan not found.")
    return scan


@router.get("/scans/{scan_id}/pdf")
async def download_pdf(
    scan_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    plan = user.plan
    limits = get_limits(plan)
    if not limits.can_download_pdf:
        raise PlanLimitExceeded(
            "PDF download requires a paid plan. "
            "Upgrade to Starter or higher."
        )

    result = await db.execute(
        select(Scan)
        .where(Scan.id == scan_id, Scan.user_id == user.id)
        .options(
            selectinload(Scan.findings),
            selectinload(Scan.domain),
        )
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise NotFound("Scan not found.")
    if scan.status != ScanStatus.COMPLETED:
        raise NotFound("Scan not yet complete.")

    # La ruta depende del branding: así, si el usuario cambia de
    # plan, no se le sirve el PDF cacheado con la marca anterior.
    target = _pdf_path_for(scan.id, limits.white_label)
    if target.exists():
        pdf_path = str(target)
    else:
        pdf_path = await asyncio.get_event_loop().run_in_executor(
            None,
            _generate_pdf_sync,
            scan,
            user.company or "",
            limits.white_label,
        )
    if scan.pdf_path != pdf_path:
        scan.pdf_path = pdf_path
        await db.flush()

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"sajjad-report-{scan_id}.pdf",
    )


def _pdf_path_for(scan_id: uuid.UUID, white_label: bool) -> Path:
    reports_dir = Path(get_settings().pdf_storage_path)
    suffix = "-wl" if white_label else ""
    return reports_dir / f"scan-{scan_id}{suffix}.pdf"


def _generate_pdf_sync(
    scan: Scan,
    company_name: str = "",
    white_label: bool = False,
) -> str:
    from sajjad.models.finding import Finding as CoreFinding
    from sajjad.models.scan_result import ScanResult
    from sajjad.reporting.pdf_generator import generate_pdf

    core_findings = [
        CoreFinding(
            id=str(f.id),
            category=f.category,
            severity=f.severity,
            title=f.title,
            description=f.description,
            evidence=f.evidence or {},
            recommendation=f.recommendation,
            source_tool=f.source_tool,
            host=f.host,
            port=f.port,
            cve=f.cve,
            cvss_score=f.cvss_score,
            discovered_at=f.discovered_at,
        )
        for f in (scan.findings or [])
    ]

    raw = scan.raw_data or {}
    result = ScanResult(
        domain=scan.domain.fqdn if scan.domain else "",
        scan_id=str(scan.id),
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        subdomains=raw.get("subdomains", []),
        live_hosts=raw.get("live_hosts", []),
        open_ports={
            host: [int(p) for p in ports]
            for host, ports in (raw.get("open_ports") or {}).items()
        },
        findings=core_findings,
        risk_score=scan.risk_score or 0,
        risk_level=scan.risk_level or "low",
        summary=scan.findings_summary or {},
    )

    output_path = _pdf_path_for(scan.id, white_label)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generated = generate_pdf(
        result,
        str(output_path),
        company_name=company_name,
        white_label=white_label,
    )
    return str(generated)


@router.get("/scans/{scan_id}/stream")
async def stream_progress(
    scan_id: uuid.UUID,
    request: Request,
    user: VerifiedUser,
    db: DB,
):
    """
    Server-Sent Events stream for real-time scan progress.
    Polls DB every 2s and emits JSON events until terminal.
    """
    # Comprueba la propiedad del scan antes de abrir el stream; el
    # resultado no se usa, sólo importa que no lance.
    await _get_user_scan(scan_id, user.id, db)

    async def _event_generator() -> AsyncGenerator[str, None]:
        while True:
            if await request.is_disconnected():
                break

            # Refresh from DB
            result = await db.execute(
                select(Scan).where(Scan.id == scan_id)
            )
            s = result.scalar_one_or_none()
            if s is None:
                break

            event = {
                "scan_id": str(s.id),
                "status": s.status.value,
                "stage": s.progress_stage,
                "risk_score": s.risk_score,
                "risk_level": s.risk_level,
                "findings_count": s.findings_count,
            }
            yield f"data: {json.dumps(event)}\n\n"

            if s.is_terminal:
                break

            await asyncio.sleep(2)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/domains/{domain_id}/scans",
    response_model=list[ScanOut],
)
async def list_domain_scans(
    domain_id: uuid.UUID,
    user: VerifiedUser,
    db: DB,
):
    await _get_verified_domain(domain_id, user.id, db)

    result = await db.execute(
        select(Scan)
        .where(Scan.domain_id == domain_id, Scan.user_id == user.id)
        .order_by(desc(Scan.started_at))
        .limit(50)
    )
    return result.scalars().all()


async def _get_user_scan(
    scan_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DB,
) -> Scan:
    result = await db.execute(
        select(Scan).where(
            Scan.id == scan_id,
            Scan.user_id == user_id,
        )
    )
    scan = result.scalar_one_or_none()
    if scan is None:
        raise NotFound("Scan not found.")
    return scan


async def _get_verified_domain(
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
    if not domain.is_verified:
        from app.core.exceptions import DomainNotVerified

        raise DomainNotVerified(
            f"Domain '{domain.fqdn}' is not verified. "
            f"Add the DNS TXT record and verify ownership first."
        )
    return domain
