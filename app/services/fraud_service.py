from __future__ import annotations

from datetime import timedelta

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.schemas.fraud import FraudAnalysisRead
from app.schemas.fraud import FraudCheckRequest

HIGH_RISK_GARAGES = {
    "RAPID CASH GARAGE",
    "NATIONAL ACCIDENT REBUILDERS",
    "METRO COLLISION HUB",
}


def analyze_claim_for_fraud(
    session: Session,
    claim: Claim,
    payload: FraudCheckRequest | None = None,
) -> FraudAnalysisRead:
    request = payload or FraudCheckRequest()
    normalized_garage = normalize_garage_name(request.garage_name)

    triggered_rules: list[str] = []
    risk_score = 0

    duplicate_claim_count = find_duplicate_claim_count(session, claim)
    if duplicate_claim_count > 0:
        triggered_rules.append("duplicate_claim_detected")
        risk_score += 3

    repeated_incident_count = find_repeated_incident_count(session, claim)
    if repeated_incident_count >= 2:
        triggered_rules.append("repeated_incident_pattern")
        risk_score += 2

    suspicious_repair_cost = is_suspicious_repair_cost(
        claim_amount=float(claim.claim_amount),
        repair_estimate_amount=request.repair_estimate_amount,
    )
    if suspicious_repair_cost:
        triggered_rules.append("suspicious_repair_cost")
        risk_score += 2

    high_risk_garage = (
        normalized_garage in HIGH_RISK_GARAGES if normalized_garage else False
    )
    if high_risk_garage:
        triggered_rules.append("high_risk_garage")
        risk_score += 3

    risk_level = "LOW"
    if risk_score >= 6:
        risk_level = "HIGH"
    elif risk_score >= 3:
        risk_level = "MEDIUM"

    return FraudAnalysisRead(
        claim_id=str(claim.id),
        risk_level=risk_level,
        risk_score=risk_score,
        triggered_rules=triggered_rules,
        duplicate_claim_count=duplicate_claim_count,
        repeated_incident_count=repeated_incident_count,
        suspicious_repair_cost=suspicious_repair_cost,
        high_risk_garage=high_risk_garage,
        garage_name=request.garage_name,
        repair_estimate_amount=request.repair_estimate_amount,
    )


def find_duplicate_claim_count(session: Session, claim: Claim) -> int:
    statement = (
        select(func.count())
        .select_from(Claim)
        .where(
            and_(
                Claim.id != claim.id,
                Claim.policy_number == claim.policy_number,
                Claim.vehicle_number == claim.vehicle_number,
                Claim.incident_date == claim.incident_date,
            )
        )
    )
    return int(session.scalar(statement) or 0)


def find_repeated_incident_count(session: Session, claim: Claim) -> int:
    window_start = claim.incident_date - timedelta(days=90)
    statement = (
        select(func.count())
        .select_from(Claim)
        .where(
            and_(
                Claim.id != claim.id,
                Claim.vehicle_number == claim.vehicle_number,
                Claim.incident_date >= window_start,
                Claim.incident_date <= claim.incident_date,
            )
        )
    )
    return int(session.scalar(statement) or 0)


def is_suspicious_repair_cost(
    claim_amount: float,
    repair_estimate_amount: float | None,
) -> bool:
    if repair_estimate_amount is None:
        return False

    return repair_estimate_amount >= max(claim_amount * 1.5, 300000)


def normalize_garage_name(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = " ".join(value.strip().upper().split())
    return collapsed or None
