from __future__ import annotations

import math
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.claim import ClaimStatus
from app.models.settlement import Settlement
from app.models.settlement import SettlementStatus
from app.schemas.settlement import InitiatePayoutRequest
from app.services.audit_service import record_audit_event


class PayoutError(ValueError):
    pass


def _backoff_delay(retry_count: int, base: float = 30.0, cap: float = 600.0) -> float:
    return min(base * math.pow(2, retry_count), cap)


def initiate_payout(
    session: Session,
    claim: Claim,
    payload: InitiatePayoutRequest,
) -> Settlement:
    if claim.status != ClaimStatus.APPROVED:
        raise PayoutError(
            f"Payout can only be initiated for APPROVED claims, current status: {claim.status}"
        )

    existing = (
        session.query(Settlement)
        .filter(
            Settlement.claim_id == claim.id,
            Settlement.status.in_(
                [SettlementStatus.INITIATED, SettlementStatus.PROCESSING]
            ),
        )
        .first()
    )
    if existing:
        raise PayoutError("An active settlement already exists for this claim")

    settlement = Settlement(
        claim_id=claim.id,
        payout_amount=payload.payout_amount,
        payment_method=payload.payment_method,
        beneficiary_name=payload.beneficiary_name,
        beneficiary_account=payload.beneficiary_account,
        bank_ifsc=payload.bank_ifsc,
        status=SettlementStatus.INITIATED,
    )
    session.add(settlement)
    session.flush()

    record_audit_event(
        session,
        entity_type="settlement",
        entity_id=str(settlement.id),
        claim_id=claim.id,
        action="PAYOUT_INITIATED",
        details={
            "settlement_id": str(settlement.id),
            "payout_amount": float(payload.payout_amount),
            "payment_method": payload.payment_method.value,
        },
    )
    session.commit()
    session.refresh(settlement)
    return settlement


def process_payout(session: Session, settlement: Settlement) -> Settlement:
    """Simulate payout processing — succeeds if retry_count is even, fails if odd."""
    settlement.status = SettlementStatus.PROCESSING
    session.commit()

    simulated_success = settlement.retry_count % 2 == 0

    if simulated_success:
        settlement.status = SettlementStatus.COMPLETED
        settlement.completed_at = datetime.now(tz=timezone.utc)
        settlement.transaction_reference = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        settlement.failure_reason = None
        record_audit_event(
            session,
            entity_type="settlement",
            entity_id=str(settlement.id),
            claim_id=settlement.claim_id,
            action="PAYOUT_COMPLETED",
            details={
                "transaction_reference": settlement.transaction_reference,
                "payout_amount": float(settlement.payout_amount),
            },
        )
    else:
        settlement.failure_reason = "Simulated bank gateway timeout"
        _schedule_payout_retry(session, settlement)
        record_audit_event(
            session,
            entity_type="settlement",
            entity_id=str(settlement.id),
            claim_id=settlement.claim_id,
            action="PAYOUT_FAILED",
            details={
                "retry_count": settlement.retry_count,
                "failure_reason": settlement.failure_reason,
            },
        )

    session.commit()
    session.refresh(settlement)
    return settlement


def _schedule_payout_retry(session: Session, settlement: Settlement) -> None:
    if settlement.retry_count >= settlement.max_retries:
        settlement.status = SettlementStatus.FAILED
        return

    delay = _backoff_delay(settlement.retry_count)
    settlement.next_retry_at = datetime.now(tz=timezone.utc) + timedelta(seconds=delay)
    settlement.retry_count += 1
    settlement.status = SettlementStatus.FAILED


def get_settlement_by_id(session: Session, settlement_id: UUID) -> Settlement | None:
    return session.get(Settlement, settlement_id)


def list_settlements_for_claim(session: Session, claim_id: UUID) -> list[Settlement]:
    return (
        session.query(Settlement)
        .filter(Settlement.claim_id == claim_id)
        .order_by(Settlement.initiated_at.desc())
        .all()
    )


def list_pending_retries(session: Session) -> list[Settlement]:
    now = datetime.now(tz=timezone.utc)
    return (
        session.query(Settlement)
        .filter(
            Settlement.status == SettlementStatus.FAILED,
            Settlement.retry_count < Settlement.max_retries,
            Settlement.next_retry_at <= now,
        )
        .all()
    )


def reverse_settlement(
    session: Session,
    settlement: Settlement,
    reason: str,
) -> Settlement:
    if settlement.status != SettlementStatus.COMPLETED:
        raise PayoutError("Only COMPLETED settlements can be reversed")

    settlement.status = SettlementStatus.REVERSED
    settlement.failure_reason = reason
    record_audit_event(
        session,
        entity_type="settlement",
        entity_id=str(settlement.id),
        claim_id=settlement.claim_id,
        action="PAYOUT_REVERSED",
        details={"reason": reason},
    )
    session.commit()
    session.refresh(settlement)
    return settlement
