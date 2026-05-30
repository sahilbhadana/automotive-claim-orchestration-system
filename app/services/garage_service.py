from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.garage import Garage
from app.models.repair_estimate import RepairEstimate
from app.models.repair_estimate import RepairEstimateStatus
from app.services.audit_service import record_audit_event
from app.schemas.garage import GarageCreate
from app.schemas.garage import RepairEstimateApprovalRequest
from app.schemas.garage import RepairEstimateCreate


class RepairEstimateWorkflowError(ValueError):
    pass


def create_garage(session: Session, payload: GarageCreate) -> Garage:
    garage = Garage(**payload.model_dump())
    session.add(garage)
    session.flush()
    record_audit_event(
        session,
        entity_type="garage",
        entity_id=str(garage.id),
        action="GARAGE_CREATED",
        details=payload.model_dump(),
    )
    session.commit()
    session.refresh(garage)
    return garage


def list_garages(session: Session) -> list[Garage]:
    statement = select(Garage).order_by(Garage.city.asc(), Garage.name.asc())
    return list(session.scalars(statement).all())


def get_garage_by_id(session: Session, garage_id: UUID) -> Garage | None:
    return session.get(Garage, garage_id)


def create_repair_estimate(
    session: Session,
    claim: Claim,
    payload: RepairEstimateCreate,
) -> RepairEstimate:
    garage = get_garage_by_id(session, payload.garage_id)
    if garage is None or not garage.is_active:
        raise RepairEstimateWorkflowError("Selected garage is not available")

    estimate = RepairEstimate(
        claim_id=claim.id,
        garage_id=payload.garage_id,
        estimated_amount=payload.estimated_amount,
        notes=payload.notes,
    )
    session.add(estimate)
    session.flush()
    record_audit_event(
        session,
        entity_type="repair_estimate",
        entity_id=str(estimate.id),
        claim_id=claim.id,
        action="REPAIR_ESTIMATE_SUBMITTED",
        details={
            "garage_id": str(payload.garage_id),
            "estimated_amount": payload.estimated_amount,
            "notes": payload.notes,
        },
    )
    session.commit()
    session.refresh(estimate)
    return estimate


def list_claim_repair_estimates(session: Session, claim_id: UUID) -> list[RepairEstimate]:
    statement = (
        select(RepairEstimate)
        .where(RepairEstimate.claim_id == claim_id)
        .order_by(RepairEstimate.created_at.desc())
    )
    return list(session.scalars(statement).all())


def get_repair_estimate_by_id(
    session: Session,
    estimate_id: UUID,
) -> RepairEstimate | None:
    return session.get(RepairEstimate, estimate_id)


def approve_repair_estimate(
    session: Session,
    estimate: RepairEstimate,
    payload: RepairEstimateApprovalRequest,
) -> RepairEstimate:
    if estimate.status != RepairEstimateStatus.SUBMITTED:
        raise RepairEstimateWorkflowError("Estimate has already been decided")

    estimate.status = (
        RepairEstimateStatus.APPROVED
        if payload.approved
        else RepairEstimateStatus.REJECTED
    )
    estimate.approval_notes = payload.approval_notes
    session.add(estimate)
    record_audit_event(
        session,
        entity_type="repair_estimate",
        entity_id=str(estimate.id),
        claim_id=estimate.claim_id,
        action="REPAIR_ESTIMATE_DECIDED",
        details={
            "status": estimate.status.value,
            "approval_notes": payload.approval_notes,
        },
    )
    session.commit()
    session.refresh(estimate)
    return estimate
