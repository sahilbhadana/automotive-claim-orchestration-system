from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "claim_workflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.claim_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Calcutta",
    enable_utc=True,
    task_track_started=True,
)
