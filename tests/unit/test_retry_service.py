"""Unit tests for the retry service and dead-letter queue logic."""

from __future__ import annotations


from app.models.failed_task import FailedTaskStatus
from app.services.retry_service import compute_backoff_delay
from app.services.retry_service import dismiss_failed_task
from app.services.retry_service import get_failed_task_by_id
from app.services.retry_service import list_dead_letter_queue
from app.services.retry_service import record_failed_task
from app.services.retry_service import requeue_failed_task
from app.services.retry_service import schedule_retry


class TestExponentialBackoff:
    def test_first_retry_is_base_delay(self):
        assert compute_backoff_delay(0, base_delay=2.0) == 2.0

    def test_second_retry_doubles(self):
        assert compute_backoff_delay(1, base_delay=2.0) == 4.0

    def test_delay_caps_at_max(self):
        assert compute_backoff_delay(100, base_delay=2.0, max_delay=300.0) == 300.0

    def test_delay_never_exceeds_cap(self):
        for i in range(20):
            assert compute_backoff_delay(i, max_delay=300.0) <= 300.0

    def test_delay_grows_exponentially(self):
        d0 = compute_backoff_delay(0)
        d1 = compute_backoff_delay(1)
        d2 = compute_backoff_delay(2)
        assert d1 == d0 * 2
        assert d2 == d0 * 4


class TestRecordFailedTask:
    def test_creates_pending_entry(self, db_session):
        task = record_failed_task(
            session=db_session,
            task_name="claims.run_fraud_checks",
            error_message="Connection refused",
            error_type="ConnectionError",
        )
        assert task.id is not None
        assert task.status == FailedTaskStatus.PENDING
        assert task.retry_count == 0
        assert task.task_name == "claims.run_fraud_checks"

    def test_stores_args_as_json(self, db_session):
        task = record_failed_task(
            session=db_session,
            task_name="claims.assign_adjuster",
            error_message="Timeout",
            error_type="TimeoutError",
            task_args=["claim-uuid-123"],
            task_kwargs={"priority": "high"},
        )
        assert "claim-uuid-123" in task.task_args
        assert "priority" in task.task_kwargs


class TestScheduleRetry:
    def test_increments_retry_count(self, db_session):
        task = record_failed_task(
            db_session, "test.task", "error", "ValueError", max_retries=3
        )
        updated = schedule_retry(db_session, task)
        assert updated.retry_count == 1
        assert updated.status == FailedTaskStatus.RETRYING
        assert updated.next_retry_at is not None

    def test_marks_dead_when_retries_exhausted(self, db_session):
        task = record_failed_task(
            db_session, "test.exhausted", "error", "ValueError", max_retries=2
        )
        task.retry_count = 2
        db_session.commit()
        updated = schedule_retry(db_session, task)
        assert updated.status == FailedTaskStatus.DEAD

    def test_retries_exhaust_to_dead_after_max(self, db_session):
        task = record_failed_task(db_session, "test.drain", "err", "Err", max_retries=3)
        # Need 4 calls: 0→1, 1→2, 2→3, then 3 >= max_retries triggers DEAD
        for _ in range(4):
            task = schedule_retry(db_session, task)
            db_session.refresh(task)
        assert task.status == FailedTaskStatus.DEAD


class TestDeadLetterQueue:
    def test_lists_only_dead_tasks(self, db_session):
        record_failed_task(db_session, "live.task", "err", "Err")
        dead_task = record_failed_task(db_session, "dead.task", "err", "Err")
        dead_task.status = FailedTaskStatus.DEAD
        db_session.commit()

        dlq = list_dead_letter_queue(db_session)
        assert all(t.status == FailedTaskStatus.DEAD for t in dlq)

    def test_requeue_resets_state(self, db_session):
        task = record_failed_task(db_session, "requeue.task", "err", "Err")
        task.status = FailedTaskStatus.DEAD
        task.retry_count = 3
        db_session.commit()

        requeued = requeue_failed_task(db_session, task.id)
        assert requeued.status == FailedTaskStatus.PENDING
        assert requeued.retry_count == 0

    def test_dismiss_removes_entry(self, db_session):
        task = record_failed_task(db_session, "dismiss.task", "err", "Err")
        task_id = task.id
        dismissed = dismiss_failed_task(db_session, task_id)
        assert dismissed is True
        assert get_failed_task_by_id(db_session, task_id) is None

    def test_requeue_nonexistent_returns_none(self, db_session):
        import uuid

        result = requeue_failed_task(db_session, uuid.uuid4())
        assert result is None
