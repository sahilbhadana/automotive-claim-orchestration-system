"""Integration tests for the settlement and payout workflow."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.models.claim import Claim, ClaimStatus
from app.models.settlement import PaymentMethod, SettlementStatus
from app.schemas.settlement import InitiatePayoutRequest
from app.services.settlement_service import (
    get_settlement_by_id,
    initiate_payout,
    list_settlements_for_claim,
    list_pending_retries,
    process_payout,
    reverse_settlement,
)


def _make_approved_claim(session) -> Claim:
    claim = Claim(
        id=uuid.uuid4(),
        policy_number=f"POL-{uuid.uuid4().hex[:6].upper()}",
        vehicle_number="KA01AB1234",
        incident_date=date(2026, 3, 1),
        incident_city="Bangalore",
        claim_amount=95000.0,
        description="Integration test claim",
        status=ClaimStatus.APPROVED,
    )
    session.add(claim)
    session.flush()
    return claim


def _payout_request(**overrides) -> InitiatePayoutRequest:
    base = {
        "payout_amount": 90000.0,
        "payment_method": PaymentMethod.NEFT,
        "beneficiary_name": "Priya Sharma",
        "beneficiary_account": "9876543210",
        "bank_ifsc": "HDFC0001234",
    }
    base.update(overrides)
    return InitiatePayoutRequest(**base)


class TestSettlementLifecycle:
    def test_full_successful_payout_flow(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _payout_request())

        assert settlement.status == SettlementStatus.INITIATED
        assert settlement.claim_id == claim.id

        settlement.retry_count = 0
        db_session.commit()
        completed = process_payout(db_session, settlement)
        assert completed.status == SettlementStatus.COMPLETED
        assert completed.transaction_reference is not None

    def test_failed_payout_schedules_retry(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _payout_request())
        settlement.retry_count = 1
        db_session.commit()

        result = process_payout(db_session, settlement)
        assert result.status == SettlementStatus.FAILED
        assert result.next_retry_at is not None
        assert result.retry_count == 2

    def test_settlements_listed_by_claim(self, db_session):
        claim = _make_approved_claim(db_session)
        initiate_payout(db_session, claim, _payout_request())

        settlements = list_settlements_for_claim(db_session, claim.id)
        assert len(settlements) >= 1
        assert all(s.claim_id == claim.id for s in settlements)

    def test_get_settlement_by_id(self, db_session):
        claim = _make_approved_claim(db_session)
        created = initiate_payout(db_session, claim, _payout_request())
        fetched = get_settlement_by_id(db_session, created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_pending_retries_are_discoverable(self, db_session):
        from datetime import datetime, timezone, timedelta

        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _payout_request())
        settlement.retry_count = 1
        db_session.commit()
        process_payout(db_session, settlement)

        settlement.next_retry_at = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
        db_session.commit()

        pending = list_pending_retries(db_session)
        assert any(s.id == settlement.id for s in pending)

    def test_reversal_flow(self, db_session):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(db_session, claim, _payout_request())
        settlement.status = SettlementStatus.COMPLETED
        db_session.commit()

        reversed_s = reverse_settlement(db_session, settlement, "Fraud reversal")
        assert reversed_s.status == SettlementStatus.REVERSED


class TestPaymentMethods:
    @pytest.mark.parametrize("method", list(PaymentMethod))
    def test_all_payment_methods_accepted(self, db_session, method):
        claim = _make_approved_claim(db_session)
        settlement = initiate_payout(
            db_session, claim, _payout_request(payment_method=method)
        )
        assert settlement.payment_method == method
