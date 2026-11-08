"""
Tests del worker de escaneo (Celery), el pegamento más crítico:
toma el resultado del pipeline y lo persiste (estado, findings,
contadores). Son tests SÍNCRONOS porque el worker usa Session
síncrona; mockeamos el pipeline y el email para no tocar red.
"""

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.domain import Domain
from app.models.scan import Finding as FindingORM
from app.models.scan import Scan, ScanStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.workers import scan_task

SYNC_URL = "postgresql+psycopg2://sajjad:sajjad@localhost:5432/sajjad_test"


def _fake_finding():
    return SimpleNamespace(
        category="tls",
        severity="high",
        severity_rank=1,
        title="Certificado vencido",
        description="El certificado TLS expiró.",
        evidence={"expired": True},
        recommendation="Renovar el certificado.",
        cvss_score=7.5,
        cve=None,
        source_tool="tlsx",
        host="example.com",
        port=443,
        discovered_at=datetime.now(UTC),
    )


def _fake_result(findings=None):
    findings = findings if findings is not None else [_fake_finding()]
    return SimpleNamespace(
        risk_score=42,
        risk_level="medium",
        subdomains=["a.example.com", "b.example.com"],
        live_hosts=["a.example.com"],
        open_ports={"a.example.com": [443, 22, 80]},
        total_open_ports=3,
        findings=findings,
        summary={"high": len(findings), "critical": 0},
    )


@pytest.fixture
def sync_engine():
    import app.models  # noqa: F401  (registra modelos)
    from app.database import Base

    eng = create_engine(SYNC_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def seeded(sync_engine):
    """Crea user+subscription+domain+scan PENDING. Devuelve ids."""
    with Session(sync_engine) as db:
        user = User(
            email="worker@example.com",
            hashed_password="x",
            full_name="W",
            is_verified=True,
        )
        db.add(user)
        db.flush()
        db.add(
            Subscription(user_id=user.id, plan="starter")
        )
        domain = Domain(
            user_id=user.id,
            fqdn="example.com",
            verified_at=datetime.now(UTC),
        )
        db.add(domain)
        db.flush()
        scan = Scan(domain_id=domain.id, user_id=user.id)
        db.add(scan)
        db.commit()
        return {
            "user_id": user.id,
            "domain_id": domain.id,
            "scan_id": str(scan.id),
        }


def test_persist_results_writes_everything(sync_engine, seeded):
    scan_task._persist_results(
        seeded["scan_id"], _fake_result(), sync_engine
    )

    with Session(sync_engine) as db:
        scan = db.get(Scan, uuid.UUID(seeded["scan_id"]))
        assert scan.status == ScanStatus.COMPLETED
        assert scan.completed_at is not None
        assert scan.risk_score == 42
        assert scan.risk_level == "medium"
        assert scan.subdomains_count == 2
        assert scan.live_hosts_count == 1
        assert scan.open_ports_count == 3
        assert scan.findings_count == 1
        assert scan.findings_summary == {"high": 1, "critical": 0}
        assert scan.raw_data["subdomains"] == [
            "a.example.com",
            "b.example.com",
        ]
        # Sin esto el PDF se regenera sin puertos y afirma que no
        # se detectó ninguno, contradiciendo open_ports_count.
        assert scan.raw_data["open_ports"] == {
            "a.example.com": [22, 80, 443]
        }

        findings = (
            db.execute(
                select(FindingORM).where(
                    FindingORM.scan_id == scan.id
                )
            )
            .scalars()
            .all()
        )
        assert len(findings) == 1
        assert findings[0].title == "Certificado vencido"
        assert findings[0].port == 443

        sub = (
            db.execute(
                select(Subscription).where(
                    Subscription.user_id == seeded["user_id"]
                )
            )
            .scalar_one()
        )
        assert sub.scans_this_month == 1


def test_mark_failed_sets_status_and_error(sync_engine, seeded):
    scan_task._mark_failed(
        seeded["scan_id"], "boom" * 300, sync_engine
    )
    with Session(sync_engine) as db:
        scan = db.get(Scan, uuid.UUID(seeded["scan_id"]))
        assert scan.status == ScanStatus.FAILED
        assert scan.completed_at is not None
        # error_message se trunca a 500 chars.
        assert len(scan.error_message) == 500


def test_run_scan_success_path(sync_engine, seeded, monkeypatch):
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    monkeypatch.setattr(
        scan_task,
        "_execute_pipeline",
        lambda scan_id, domain, engine: _fake_result(),
    )
    monkeypatch.setattr(
        scan_task, "_notify_user", lambda scan_id, engine: None
    )

    out = scan_task.run_scan(seeded["scan_id"])
    assert out["status"] == "completed"
    assert out["risk_score"] == 42

    with Session(sync_engine) as db:
        scan = db.get(Scan, uuid.UUID(seeded["scan_id"]))
        assert scan.status == ScanStatus.COMPLETED


def test_run_scan_failure_marks_failed_and_raises(
    sync_engine, seeded, monkeypatch
):
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )

    def _boom(scan_id, domain, engine):
        raise RuntimeError("pipeline exploded")

    monkeypatch.setattr(scan_task, "_execute_pipeline", _boom)

    with pytest.raises(RuntimeError):
        scan_task.run_scan(seeded["scan_id"])

    with Session(sync_engine) as db:
        scan = db.get(Scan, uuid.UUID(seeded["scan_id"]))
        assert scan.status == ScanStatus.FAILED
        assert "pipeline exploded" in scan.error_message


def test_run_scan_idempotent_when_already_completed(
    sync_engine, seeded, monkeypatch
):
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    # Marcar el scan como ya completado.
    with Session(sync_engine) as db:
        scan = db.get(Scan, uuid.UUID(seeded["scan_id"]))
        scan.status = ScanStatus.COMPLETED
        db.commit()

    # No debe re-ejecutar el pipeline.
    def _should_not_run(*a, **k):
        raise AssertionError("pipeline no debería ejecutarse")

    monkeypatch.setattr(
        scan_task, "_execute_pipeline", _should_not_run
    )

    out = scan_task.run_scan(seeded["scan_id"])
    assert out["status"] == "completed"


def test_run_scan_missing_scan_returns_error(
    sync_engine, monkeypatch
):
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    out = scan_task.run_scan(str(uuid.uuid4()))
    assert out == {"error": "scan_not_found"}


def test_schedule_due_scans_launches_for_verified_paid_domain(
    sync_engine, seeded, monkeypatch
):
    """El beat auto-lanza un scan para un dominio verificado de un
    plan con intervalo, sin escaneos previos, y lo PERSISTE antes
    de encolar (la tarea debe poder leerlo por id)."""
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    # El dominio no debe tener scans en curso para ser elegible.
    with Session(sync_engine) as db:
        db.delete(db.get(Scan, uuid.UUID(seeded["scan_id"])))
        db.commit()

    enqueued: list[str] = []

    def _capture_delay(scan_id):
        # El scan ya debe existir en la BD cuando se encola.
        with Session(sync_engine) as db:
            assert db.get(Scan, uuid.UUID(scan_id)) is not None
        enqueued.append(scan_id)
        return SimpleNamespace(id="task")

    monkeypatch.setattr(scan_task.run_scan, "delay", _capture_delay)

    out = scan_task.schedule_due_scans()
    assert out["launched"] == 1
    assert len(enqueued) == 1

    with Session(sync_engine) as db:
        scan = db.get(Scan, uuid.UUID(enqueued[0]))
        assert scan.domain_id == seeded["domain_id"]
        assert scan.status == ScanStatus.PENDING


def test_schedule_due_scans_skips_when_recent_scan_exists(
    sync_engine, seeded, monkeypatch
):
    """No relanza si ya hay un scan completado dentro del intervalo
    del plan (starter = cada 7 días)."""
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    with Session(sync_engine) as db:
        scan = db.get(Scan, uuid.UUID(seeded["scan_id"]))
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.now(UTC)
        db.commit()

    monkeypatch.setattr(
        scan_task.run_scan,
        "delay",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("no debería encolar")
        ),
    )

    out = scan_task.schedule_due_scans()
    assert out["launched"] == 0


# ── Expiración de pruebas gratuitas ─────────────────────────


def _set_plan(sync_engine, plan, trial_ends_at):
    with Session(sync_engine) as db:
        sub = db.execute(select(Subscription)).scalar_one()
        sub.plan = plan
        sub.trial_ends_at = trial_ends_at
        db.commit()


def _read_sub(sync_engine):
    with Session(sync_engine) as db:
        return db.execute(select(Subscription)).scalar_one()


def test_expire_trials_downgrades_expired(
    sync_engine, seeded, monkeypatch
):
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    _set_plan(
        sync_engine,
        "trial",
        datetime.now(UTC) - timedelta(days=1),
    )

    out = scan_task.expire_trials()
    assert out["expired"] == 1

    sub = _read_sub(sync_engine)
    assert sub.plan == "free"
    # La marca se conserva: es lo que impide otorgar un segundo trial.
    assert sub.trial_ends_at is not None


def test_expire_trials_leaves_active_trial(
    sync_engine, seeded, monkeypatch
):
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    _set_plan(
        sync_engine,
        "trial",
        datetime.now(UTC) + timedelta(days=5),
    )

    assert scan_task.expire_trials()["expired"] == 0
    assert _read_sub(sync_engine).plan == "trial"


def test_expire_trials_ignores_paid_plans(
    sync_engine, seeded, monkeypatch
):
    """Una fecha vieja en un plan de pago no debe degradarlo."""
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    _set_plan(
        sync_engine,
        "professional",
        datetime.now(UTC) - timedelta(days=30),
    )

    assert scan_task.expire_trials()["expired"] == 0
    assert _read_sub(sync_engine).plan == "professional"


def test_schedule_skips_expired_trial(
    sync_engine, seeded, monkeypatch
):
    """
    Un trial vencido no recibe escaneos automáticos aunque el beat de
    expiración todavía no haya corrido.
    """
    monkeypatch.setattr(
        scan_task, "_sync_engine", lambda: sync_engine
    )
    _set_plan(
        sync_engine,
        "trial",
        datetime.now(UTC) - timedelta(days=1),
    )
    monkeypatch.setattr(
        scan_task.run_scan,
        "delay",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("no debería encolar")
        ),
    )

    assert scan_task.schedule_due_scans()["launched"] == 0
