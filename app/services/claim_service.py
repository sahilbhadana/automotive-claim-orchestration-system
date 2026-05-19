from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.claim import ClaimStatus
from app.schemas.claim import ClaimCreate


def create_claim(session: Session, payload: ClaimCreate) -> Claim:
    claim = Claim(**payload.model_dump())
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim


def list_claims(session: Session) -> list[Claim]:
    statement = select(Claim).order_by(Claim.created_at.desc())
    return list(session.scalars(statement).all())


def get_claim_by_id(session: Session, claim_id: UUID) -> Claim | None:
    return session.get(Claim, claim_id)


def update_claim_status(session: Session, claim: Claim, status: ClaimStatus) -> Claim:
    claim.status = status
    session.add(claim)
    session.commit()
    session.refresh(claim)
    return claim
