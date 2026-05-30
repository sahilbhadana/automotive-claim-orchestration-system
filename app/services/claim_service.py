from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.claim import ClaimStatus
from app.services.audit_service import record_audit_event
from app.schemas.claim import ClaimCreate


def create_claim(session: Session, payload: ClaimCreate) -> Claim:
    claim = Claim(**payload.model_dump())
    session.add(claim)
    session.flush()
    record_audit_event(
        session,
        entity_type="claim",
        entity_id=str(claim.id),
        claim_id=claim.id,
        action="CLAIM_CREATED",
        details={
            "policy_number": claim.policy_number,
            "vehicle_number": claim.vehicle_number,
            "incident_city": claim.incident_city,
            "claim_amount": float(claim.claim_amount),
            "status": claim.status.value,
        },
    )
    session.commit()
    session.refresh(claim)
    return claim


def list_claims(session: Session) -> list[Claim]:
    statement = select(Claim).order_by(Claim.created_at.desc())
    return list(session.scalars(statement).all())


def get_claim_by_id(session: Session, claim_id: UUID) -> Claim | None:
    return session.get(Claim, claim_id)


def update_claim_status(session: Session, claim: Claim, status: ClaimStatus) -> Claim:
    previous_status = claim.status
    claim.status = status
    session.add(claim)
    record_audit_event(
        session,
        entity_type="claim",
        entity_id=str(claim.id),
        claim_id=claim.id,
        action="CLAIM_STATUS_UPDATED",
        details={
            "previous_status": previous_status.value,
            "current_status": status.value,
        },
    )
    session.commit()
    session.refresh(claim)
    return claim
