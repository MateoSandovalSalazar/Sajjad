"""
Celery task: run the full scan pipeline and persist results.

Uses a synchronous SQLAlchemy session inside the task.
Celery workers are not async, and the pipeline itself is
subprocess-based (blocking I/O), so sync is correct here.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.models.domain import Domain
from app.models.scan import Finding as FindingORM
from app.models.scan import Scan, ScanStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _sync_engine():
    settings = get_settings()
    sync_url = settings.database_url.replace(
        "postgresql+asyncpg://", "postgresql://"
    )
    return create_engine(sync_url, pool_pre_ping=True)


@celery_app.task(
    bind=True,
    name="app.workers.scan_task.run_scan",
    max_retries=1,
    acks_late=True,
)
def run_scan(self, scan_id: str) -> dict:
    engine = _sync_engine()

    with Session(engine) as db:
        scan = db.execute(
            select(Scan)
            .where(Scan.id == uuid.UUID(scan_id))
            .options(selectinload(Scan.domain))
        ).scalar_one_or_none()

        if scan is None:
            logger.error("Scan %s not found", scan_id)
            return {"error": "scan_not_found"}

        if scan.status not in (
            ScanStatus.PENDING,
            ScanStatus.RUNNING,
        ):
            return {"status": scan.status.value}

        domain_fqdn = scan.domain.fqdn
        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.now(timezone.utc)
        db.commit()

    try:
        result = _execute_pipeline(scan_id, domain_fqdn, engine)
        _persist_results(scan_id, result, engine)
        _notify_user(scan_id, engine)
        return {"status": "completed", "risk_score": result.risk_score}

    except Exception as exc:
        logger.exception("Scan %s failed: %s", scan_id, exc)
        _mark_failed(scan_id, str(exc), engine)
        raise


def _execute_pipeline(scan_id: str, domain: str, engine):
    from sajjad.orchestrator import ScanOrchestrator

    def on_progress(stage: str, _message: str) -> None:
        with Session(engine) as db:
            scan = db.get(Scan, uuid.UUID(scan_id))
            if scan:
                scan.progress_stage = stage.lower()
                db.commit()

    return ScanOrchestrator(
        domain=domain, on_progress=on_progress
    ).run()


def _persist_results(scan_id: str, result, engine) -> None:
    with Session(engine) as db:
        scan = db.get(Scan, uuid.UUID(scan_id))
        if scan is None:
            return

        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.now(timezone.utc)
        scan.risk_score = result.risk_score
        scan.risk_level = result.risk_level
        scan.subdomains_count = len(result.subdomains)
        scan.live_hosts_count = len(result.live_hosts)
        scan.open_ports_count = result.total_open_ports
        scan.findings_count = len(result.findings)
        scan.findings_summary = result.summary
        scan.raw_data = {
            "subdomains": result.subdomains[:500],
            "live_hosts": result.live_hosts[:200],
        }

        for f in result.findings:
            orm = FindingORM(
                scan_id=scan.id,
                category=f.category,
                severity=f.severity,
                severity_rank=f.severity_rank,
                title=f.title,
                description=f.description,
                evidence=f.evidence,
                recommendation=f.recommendation,
                cvss_score=f.cvss_score,
                cve=f.cve,
                source_tool=f.source_tool,
                host=f.host,
                port=f.port,
                discovered_at=f.discovered_at,
            )
            db.add(orm)

        sub = db.execute(
            select(Subscription).where(
                Subscription.user_id == scan.user_id
            )
        ).scalar_one_or_none()
        if sub:
            sub.scans_this_month = (sub.scans_this_month or 0) + 1

        db.commit()
        logger.info(
            "Scan %s persisted: score=%s, findings=%d",
            scan_id,
            result.risk_score,
            len(result.findings),
        )


def _mark_failed(scan_id: str, error: str, engine) -> None:
    with Session(engine) as db:
        scan = db.get(Scan, uuid.UUID(scan_id))
        if scan:
            scan.status = ScanStatus.FAILED
            scan.error_message = error[:500]
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()


def _notify_user(scan_id: str, engine) -> None:
    from app.services.email import send_scan_complete_email

    with Session(engine) as db:
        scan = db.execute(
            select(Scan)
            .where(Scan.id == uuid.UUID(scan_id))
            .options(
                selectinload(Scan.domain),
                selectinload(Scan.user),
            )
        ).scalar_one_or_none()

        if scan is None or scan.user is None:
            return

        user = scan.user
        summary = scan.findings_summary or {}

        try:
            asyncio.run(
                send_scan_complete_email(
                    email=user.email,
                    full_name=user.full_name,
                    domain=scan.domain.fqdn,
                    risk_score=scan.risk_score or 0,
                    risk_level=scan.risk_level or "unknown",
                    critical_count=summary.get("critical", 0),
                    high_count=summary.get("high", 0),
                )
            )
        except Exception as exc:
            logger.warning("Email notify failed: %s", exc)


@celery_app.task(name="app.workers.scan_task.schedule_due_scans")
def schedule_due_scans() -> dict:
    """
    Beat task: auto-launch scans for domains whose interval elapsed.
    Runs every 15 minutes.
    """
    from app.core.limits import PLANS

    engine = _sync_engine()
    launched = 0

    with Session(engine) as db:
        domains = db.execute(
            select(Domain)
            .where(Domain.verified_at.is_not(None))
            .options(
                selectinload(Domain.scans),
                selectinload(Domain.user).selectinload(
                    User.subscription
                ),
            )
        ).scalars().all()

        for domain in domains:
            user = domain.user
            sub = getattr(user, "subscription", None)

            if sub is None or sub.status != SubscriptionStatus.ACTIVE:
                continue

            limits = PLANS.get(sub.plan)
            if limits is None or limits.scan_interval_days is None:
                continue

            completed = [
                s
                for s in domain.scans
                if s.status == ScanStatus.COMPLETED
                and s.completed_at is not None
            ]
            if completed:
                last = max(completed, key=lambda s: s.completed_at)
                due_after = last.completed_at + timedelta(
                    days=limits.scan_interval_days
                )
                if datetime.now(timezone.utc) < due_after:
                    continue

            running = any(
                s.status in (ScanStatus.PENDING, ScanStatus.RUNNING)
                for s in domain.scans
            )
            if running:
                continue

            new_scan = Scan(
                domain_id=domain.id,
                user_id=user.id,
            )
            db.add(new_scan)
            db.flush()

            run_scan.delay(str(new_scan.id))
            launched += 1
            logger.info(
                "Auto-launched scan for %s (plan=%s)",
                domain.fqdn,
                sub.plan,
            )

        db.commit()

    logger.info("schedule_due_scans: launched %d scans", launched)
    return {"launched": launched}
