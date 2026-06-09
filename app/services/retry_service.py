from __future__ import annotations

import json
import math
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.failed_task import FailedTask
from app.models.failed_task import FailedTaskStatus


def compute_backoff_delay(
    retry_count: int,
    base_delay: float = 2.0,
    max_delay: float = 300.0,
) -> float:
    """Exponential backoff with a ceiling: base_delay * 2^retry_count."""
    return min(base_delay * math.pow(2, retry_count), max_delay)


def record_failed_task(
    session: Session,
    task_name: str,
    error_message: str,
    error_type: str,
    task_args: list | None = None,
    task_kwargs: dict | None = None,
    max_retries: int = 3,
) -> FailedTask:
    entry = FailedTask(
        task_name=task_name,
        task_args=json.dumps(task_args or []),
        task_kwargs=json.dumps(task_kwargs or {}),
        error_message=error_message,
        error_type=error_type,
        max_retries=max_retries,
        status=FailedTaskStatus.PENDING,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def schedule_retry(session: Session, failed_task: FailedTask) -> FailedTask:
    if failed_task.retry_count >= failed_task.max_retries:
        failed_task.status = FailedTaskStatus.DEAD
        session.commit()
        return failed_task

    delay = compute_backoff_delay(failed_task.retry_count)
    failed_task.next_retry_at = datetime.now(tz=timezone.utc) + timedelta(seconds=delay)
    failed_task.retry_count += 1
    failed_task.status = FailedTaskStatus.RETRYING
    session.commit()
    session.refresh(failed_task)
    return failed_task


def mark_task_recovered(session: Session, failed_task: FailedTask) -> FailedTask:
    failed_task.status = FailedTaskStatus.RECOVERED
    failed_task.recovered_at = datetime.now(tz=timezone.utc)
    session.commit()
    session.refresh(failed_task)
    return failed_task


def list_failed_tasks(
    session: Session,
    status: FailedTaskStatus | None = None,
) -> list[FailedTask]:
    query = session.query(FailedTask)
    if status is not None:
        query = query.filter(FailedTask.status == status)
    return query.order_by(FailedTask.failed_at.desc()).all()


def get_failed_task_by_id(session: Session, task_id: UUID) -> FailedTask | None:
    return session.get(FailedTask, task_id)


def list_dead_letter_queue(session: Session) -> list[FailedTask]:
    return list_failed_tasks(session, status=FailedTaskStatus.DEAD)


def requeue_failed_task(session: Session, task_id: UUID) -> FailedTask | None:
    task = get_failed_task_by_id(session, task_id)
    if task is None:
        return None
    task.status = FailedTaskStatus.PENDING
    task.retry_count = 0
    task.next_retry_at = None
    session.commit()
    session.refresh(task)
    return task


def dismiss_failed_task(session: Session, task_id: UUID) -> bool:
    task = get_failed_task_by_id(session, task_id)
    if task is None:
        return False
    session.delete(task)
    session.commit()
    return True
