"""Unit tests for settlement service — payout initiation, retry, reversal."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import patch

import pytest

from app.models.claim import Claim, ClaimStatus
from app.models.settlement import PaymentMethod, Settlement, SettlementStatus
from app.schemas.settlement import InitiatePayoutRequest
from app.services.settlement_service import (
    PayoutError,
    _backoff_delay,
    initiate_payout,
    list_pending_retries,
    process_payout,
    reverse_settlement,
)


def _make_approved_claim(session) -> Claim:
    claim = Claim(
        id=uuid.uuid4(),
        policy_number="POL-SETTLE-001",
        vehicle_number="DL01XY9999",
        incident_date=date(2026, 2, 1),
        incident_city="Delhi",
        claim_amount=120000.0,
        description="Settlement test claim",
        status=ClaimStatus.APPROVED,
    )
    session.add(claim)
    session.flush()
    return claim


def _make_payout_request(**kwargs) -> InitiatePayoutRequest:
    defaults = {
        "payout_amount": 100000.0,
        "payment_method": PaymentMethod.BANK_TRANSFER,
        "beneficiary_name": "Ravi Kumar",
        "beneficiary_account": "1234567890",
        "bank_ifsc": "SBIN0001234",
    }
    defaults.update(kwargs)
    return InitiatePayoutRequest(**defaults)


class TestBackoffDelay:
    def test_first_attempt_is_base(self):
        assert _backoff_delay(0, base=30.0) == 30.0

    def test_doubles_each_retry(self):
        assert _backoff_delay(1, base=30.0) == 60.0
        assert _backoff_delay(2, base=30.0) == 120.0

    def test_caps_at_maximum(self):
        assert _backoff_delay(10, cap=600.0) == 600.0


class TestInitiatePayout:
    def test_creates_settlement_for_approved_claim(self, db_session):
        claim = _make_approved_claim(db_session)
        req = _make_payout_request()
        settlement = initiate_payout(db_session, claim, req)
        assert settlement.id is not None
        assert settlement.status == SettlementStatus.INITIATED
        assert settlement.claim_id == claim.id
        assert float(settlement.payout_amount) == 100000.0

    def test_rejects_non_approved_claim(self, db_session):
        claim = _make_approved_claim(db_session)
        claim.status = ClaimStatus.FRAUD_ANALYSIS
        db_session.commit()
        with pytest.raises(PayoutError, match="APPROVED"):
            initiate_payout(db_session, claim, _make_payout_request())

    def test_rejects_duplicate_active_settlement(self, db_session):
        claim = _make_approved_claim(db_session)
        initiate_payout(db_session, claim, _make_payout_request())
        with pytest.raises(PayoutError, match="active settlement"):
            initiate_payout(db_session, claim, _make_payout_request())


class TestProcessPayout:
    def test_even_retry_count_succeeds(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _make_payout_request())
        settlement.retry_count = 0
        db_session.commit()
        result = process_payout(db_session, settlement)
        assert result.status == SettlementStatus.COMPLETED
        assert result.transaction_reference is not None

    def test_odd_retry_count_fails(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _make_payout_request())
        settlement.retry_count = 1
        db_session.commit()
        result = process_payout(db_session, settlement)
        assert result.status == SettlementStatus.FAILED
        assert result.failure_reason is not None

    def test_schedules_retry_with_backoff(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _make_payout_request())
        settlement.retry_count = 1
        db_session.commit()
        result = process_payout(db_session, settlement)
        assert result.next_retry_at is not None

    def test_exhausted_retries_stay_failed(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _make_payout_request())
        settlement.retry_count = 3
        settlement.max_retries = 3
        db_session.commit()
        result = process_payout(db_session, settlement)
        assert result.status == SettlementStatus.FAILED


class TestReverseSettlement:
    def test_reverses_completed_settlement(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _make_payout_request())
        settlement.status = SettlementStatus.COMPLETED
        db_session.commit()
        reversed_s = reverse_settlement(db_session, settlement, "Customer dispute")
        assert reversed_s.status == SettlementStatus.REVERSED
        assert reversed_s.failure_reason == "Customer dispute"

    def test_cannot_reverse_non_completed(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _make_payout_request())
        with pytest.raises(PayoutError, match="COMPLETED"):
            reverse_settlement(db_session, settlement, "mistake")
