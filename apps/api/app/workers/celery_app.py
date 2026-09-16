"""Celery application for long-running work (PDF generation, parsing, AI jobs).

Runs as a separate process/container from the API:

    celery -A app.workers.celery_app worker --loglevel INFO

Tasks receive IDs, never whole objects, and load what they need from PostgreSQL, so a
retried task always works from the current source of truth.
"""

from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.sentry import configure_sentry

settings = get_settings()
configure_logging(settings)
configure_sentry(settings)

celery_app = Celery("workaholic", broker=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    # Durable job state lives in PostgreSQL; Celery's result backend is not used.
    task_ignore_result=True,
    # Acknowledge after completion so a crashed worker's task is redelivered.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    worker_hijack_root_logger=False,
    timezone="UTC",
)
