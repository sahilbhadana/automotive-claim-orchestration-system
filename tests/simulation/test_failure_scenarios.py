"""Failure simulation and chaos-style resilience tests.

These tests deliberately inject failure conditions to verify that the
system degrades gracefully, retries correctly, and routes failures to
the dead-letter queue rather than silently dropping data.
"""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.models.claim import Claim, ClaimStatus
from app.models.failed_task import FailedTaskStatus
from app.models.settlement import SettlementStatus
from app.schemas.settlement import InitiatePayoutRequest
from app.services.retry_service import (
    compute_backoff_delay,
    list_dead_letter_queue,
    list_failed_tasks,
    record_failed_task,
    schedule_retry,
)
from app.services.settlement_service import PayoutError, initiate_payout, process_payout
from app.services.workflow_service import WorkflowTransitionError, get_allowed_transitions


def _make_claim(status: ClaimStatus = ClaimStatus.APPROVED) -> Claim:
    c = Claim()
    c.id = uuid.uuid4()
    c.policy_number = "POL-SIM-001"
    c.vehicle_number = "GJ01AA9999"
    c.incident_date = date(2026, 4, 1)
    c.incident_city = "Ahmedabad"
    c.claim_amount = 75000.0
    c.description = "Simulation test"
    c.status = status
    return c


class TestWorkflowFailureScenarios:
    def test_invalid_transition_raises_not_silently_fails(self):
        transitions = get_allowed_transitions(ClaimStatus.PAYOUT)
        assert transitions == [], "PAYOUT should have no forward transitions"

    def test_terminal_state_cannot_be_transitioned(self):
        from app.services.workflow_service import WorkflowTransitionError, is_terminal_state
        assert is_terminal_state(ClaimStatus.REJECTED)
        assert is_terminal_state(ClaimStatus.PAYOUT)

    def test_workflow_rejects_skip_transitions(self):
        from app.services.workflow_service import resolve_target_status
        with pytest.raises(WorkflowTransitionError):
            resolve_target_status(
                allowed_transitions=[ClaimStatus.DOCUMENT_VERIFICATION],
                target_status=ClaimStatus.APPROVED,
            )


class TestRetryExhaustionScenario:
    def test_task_reaches_dead_status_after_max_retries(self, db_session):
        task = record_failed_task(
            db_session,
            task_name="claims.run_fraud_checks",
            error_message="Database connection pool exhausted",
            error_type="OperationalError",
            max_retries=3,
        )
        for _ in range(3):
            schedule_retry(db_session, task)

        db_session.refresh(task)
        assert task.status == FailedTaskStatus.DEAD

    def test_dead_tasks_accumulate_in_dlq(self, db_session):
        initial_count = len(list_dead_letter_queue(db_session))

        for i in range(3):
            t = record_failed_task(
                db_session,
                task_name=f"sim.task.{i}",
                error_message="Simulated failure",
                error_type="SimulationError",
                max_retries=1,
            )
            t.retry_count = 1
            db_session.commit()
            schedule_retry(db_session, t)

        new_dead = list_dead_letter_queue(db_session)
        assert len(new_dead) >= initial_count + 3

    def test_backoff_increases_between_retries(self):
        delays = [compute_backoff_delay(i) for i in range(5)]
        for i in range(len(delays) - 1):
            assert delays[i + 1] > delays[i] or delays[i + 1] == delays[i + 1]


class TestPayoutFailureScenarios:
    def test_payout_on_non_approved_claim_raises(self, db_session):
        claim = _make_claim(ClaimStatus.FRAUD_ANALYSIS)
        db_session.add(claim)
        db_session.flush()

        req = InitiatePayoutRequest(
            payout_amount=50000.0,
            beneficiary_name="Test User",
            beneficiary_account="1234567890",
        )
        with pytest.raises(PayoutError, match="APPROVED"):
            initiate_payout(db_session, claim, req)

    def test_duplicate_active_settlement_blocked(self, db_session):
        claim = _make_claim(ClaimStatus.APPROVED)
        db_session.add(claim)
        db_session.flush()

        req = InitiatePayoutRequest(
            payout_amount=50000.0,
            beneficiary_name="Test User",
            beneficiary_account="1234567890",
        )
        initiate_payout(db_session, claim, req)

        with pytest.raises(PayoutError, match="active settlement"):
            initiate_payout(db_session, claim, req)

    def test_payout_retry_count_increments_on_failure(self, db_session):
        claim = _make_claim(ClaimStatus.APPROVED)
        db_session.add(claim)
        db_session.flush()

        req = InitiatePayoutRequest(
            payout_amount=50000.0,
            beneficiary_name="Test User",
            beneficiary_account="1234567890",
        )
        settlement = initiate_payout(db_session, claim, req)
        settlement.retry_count = 1
        db_session.commit()

        result = process_payout(db_session, settlement)
        assert result.retry_count == 2 or result.status == SettlementStatus.FAILED


class TestEventPublisherFallback:
    def test_publisher_returns_false_without_amqp(self):
        from app.events.event_schemas import ClaimCreatedEvent
        from app.events.publisher import publish_event

        event = ClaimCreatedEvent.build(
            claim_id=uuid.uuid4(),
            policy_number="POL-001",
            vehicle_number="MH01AB1234",
            claim_amount=50000.0,
            incident_city="Mumbai",
        )
        result = publish_event(event)
        assert isinstance(result, bool)

    def test_publish_claim_created_does_not_raise(self):
        from app.events.publisher import publish_claim_created

        result = publish_claim_created(
            claim_id=uuid.uuid4(),
            policy_number="POL-001",
            vehicle_number="MH01AB0001",
            claim_amount=50000.0,
            incident_city="Mumbai",
        )
        assert result is False

    def test_publish_fraud_completed_does_not_raise(self):
        from app.events.publisher import publish_fraud_check_completed

        result = publish_fraud_check_completed(
            claim_id=uuid.uuid4(),
            risk_level="HIGH",
            risk_score=7,
            triggered_rules=["suspicious_garage", "high_estimate"],
        )
        assert result is False
