"""
Celery application factory.

Beat schedule: periodic scan launcher that checks
which domains need re-scanning based on plan interval.
"""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings
from app.core.observability import configure_logging, configure_sentry


def create_celery() -> Celery:
    settings = get_settings()

    # El worker es un proceso aparte de la API: necesita su propia
    # configuración de logging y Sentry. Es además donde corren los
    # escaneos, así que es el sitio donde más importa enterarse de
    # los fallos.
    configure_logging()
    configure_sentry()

    app = Celery(
        "sajjad",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.workers.scan_task"],
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,  # fair dispatch
        result_expires=86400,  # 24h
        beat_schedule={
            "schedule-due-scans": {
                "task": "app.workers.scan_task.schedule_due_scans",
                "schedule": crontab(minute="*/15"),
            },
            "reset-monthly-scan-counts": {
                "task": "app.workers.scan_task.reset_monthly_scan_counts",
                "schedule": crontab(hour=0, minute=10),  # diario 00:10 UTC
            },
            "expire-trials": {
                "task": "app.workers.scan_task.expire_trials",
                "schedule": crontab(hour=0, minute=20),  # diario 00:20 UTC
            },
        },
    )

    return app


celery_app = create_celery()
