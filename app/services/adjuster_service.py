from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.adjuster import Adjuster
from app.models.adjuster import AdjusterExpertise
from app.models.claim import Claim
from app.models.claim import ClaimStatus
from app.services.audit_service import record_audit_event

ACTIVE_WORKLOAD_STATUSES = {
    ClaimStatus.CLAIM_CREATED,
    ClaimStatus.DOCUMENT_VERIFICATION,
    ClaimStatus.POLICY_VALIDATION,
    ClaimStatus.FRAUD_ANALYSIS,
    ClaimStatus.ADJUSTER_ASSIGNMENT,
    ClaimStatus.REPAIR_ESTIMATION,
    ClaimStatus.FINAL_APPROVAL,
    ClaimStatus.APPROVED,
}


class AdjusterAssignmentError(ValueError):
    pass


@dataclass
class RankedAdjuster:
    adjuster: Adjuster
    city_match: bool
    workload_count: int
    workload_ratio: float


def create_adjuster(
    session: Session,
    full_name: str,
    city: str,
    expertise: AdjusterExpertise,
    max_active_claims: int,
    is_active: bool,
) -> Adjuster:
    adjuster = Adjuster(
        full_name=full_name,
        city=city,
        expertise=expertise,
        max_active_claims=max_active_claims,
        is_active=is_active,
    )
    session.add(adjuster)
    session.flush()
    record_audit_event(
        session,
        entity_type="adjuster",
        entity_id=str(adjuster.id),
        action="ADJUSTER_CREATED",
        details={
            "full_name": full_name,
            "city": city,
            "expertise": expertise.value,
            "max_active_claims": max_active_claims,
            "is_active": is_active,
        },
    )
    session.commit()
    session.refresh(adjuster)
    return adjuster


def list_adjusters(session: Session) -> list[Adjuster]:
    statement = select(Adjuster).order_by(Adjuster.city.asc(), Adjuster.full_name.asc())
    return list(session.scalars(statement).all())


def get_adjuster_by_id(session: Session, adjuster_id: UUID) -> Adjuster | None:
    return session.get(Adjuster, adjuster_id)


def assign_best_adjuster(session: Session, claim: Claim) -> RankedAdjuster:
    required_expertise = determine_required_expertise(float(claim.claim_amount))
    eligible_adjusters = find_eligible_adjusters(session, claim, required_expertise)

    if not eligible_adjusters:
        raise AdjusterAssignmentError(
            "No eligible active adjuster found for this claim"
        )

    ranked = sorted(
        eligible_adjusters,
        key=lambda item: (
            not item.city_match,
            item.workload_ratio,
            item.workload_count,
            item.adjuster.full_name,
        ),
    )[0]

    claim.adjuster_id = ranked.adjuster.id
    session.add(claim)
    record_audit_event(
        session,
        entity_type="adjuster_assignment",
        entity_id=str(ranked.adjuster.id),
        claim_id=claim.id,
        action="CLAIM_ADJUSTER_ASSIGNED",
        details={
            "adjuster_id": str(ranked.adjuster.id),
            "adjuster_name": ranked.adjuster.full_name,
            "adjuster_city": ranked.adjuster.city,
            "city_match": ranked.city_match,
            "workload_count": ranked.workload_count,
            "max_active_claims": ranked.adjuster.max_active_claims,
            "assigned_expertise": ranked.adjuster.expertise.value,
            "required_expertise": required_expertise.value,
        },
    )
    session.commit()
    session.refresh(claim)
    return ranked


def determine_required_expertise(claim_amount: float) -> AdjusterExpertise:
    if claim_amount >= 500000:
        return AdjusterExpertise.FRAUD_SENSITIVE
    if claim_amount >= 200000:
        return AdjusterExpertise.HIGH_VALUE
    return AdjusterExpertise.MOTOR_GENERAL


def find_eligible_adjusters(
    session: Session,
    claim: Claim,
    required_expertise: AdjusterExpertise,
) -> list[RankedAdjuster]:
    adjusters = [
        adjuster
        for adjuster in list_adjusters(session)
        if adjuster.is_active
        and expertise_satisfies(adjuster.expertise, required_expertise)
    ]

    ranked_adjusters: list[RankedAdjuster] = []
    normalized_city = normalize_city(claim.incident_city)

    for adjuster in adjusters:
        workload_count = get_pending_workload_count(session, adjuster.id)
        if workload_count >= adjuster.max_active_claims:
            continue

        ranked_adjusters.append(
            RankedAdjuster(
                adjuster=adjuster,
                city_match=normalize_city(adjuster.city) == normalized_city,
                workload_count=workload_count,
                workload_ratio=workload_count / adjuster.max_active_claims,
            )
        )

    return ranked_adjusters


def get_pending_workload_count(session: Session, adjuster_id: UUID) -> int:
    statement = (
        select(func.count())
        .select_from(Claim)
        .where(
            Claim.adjuster_id == adjuster_id,
            Claim.status.in_(ACTIVE_WORKLOAD_STATUSES),
        )
    )
    return int(session.scalar(statement) or 0)


def expertise_satisfies(
    candidate: AdjusterExpertise,
    required: AdjusterExpertise,
) -> bool:
    rank = {
        AdjusterExpertise.MOTOR_GENERAL: 1,
        AdjusterExpertise.HIGH_VALUE: 2,
        AdjusterExpertise.FRAUD_SENSITIVE: 3,
    }
    return rank[candidate] >= rank[required]


def normalize_city(value: str) -> str:
    return " ".join(value.strip().upper().split())
