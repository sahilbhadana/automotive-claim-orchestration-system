from __future__ import annotations

from celery import Task

from app.db.session import SessionLocal
from app.services.retry_service import record_failed_task
from app.services.retry_service import schedule_retry


class ResilientTask(Task):
    """Celery base task that routes failures into the dead-letter queue.

    All tasks inheriting this base class will automatically have their
    failures persisted, with exponential-backoff retry scheduling applied
    before the entry is promoted to DEAD status.
    """

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:
        session = SessionLocal()
        try:
            entry = record_failed_task(
                session=session,
                task_name=self.name,
                error_message=str(exc),
                error_type=type(exc).__name__,
                task_args=list(args),
                task_kwargs=dict(kwargs),
                max_retries=self.max_retries or 3,
            )
            schedule_retry(session, entry)
        except Exception:
            pass
        finally:
            session.close()
        super().on_failure(exc, task_id, args, kwargs, einfo)
