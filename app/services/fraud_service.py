from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.claim import ClaimType
from app.models.document import DocumentType
from app.models.fraud_assessment import FraudAssessment
from app.schemas.fraud import FraudAnalysisRead
from app.schemas.fraud import FraudCheckRequest
from app.schemas.fraud import FraudRecommendation
from app.schemas.fraud import FraudSignal
from app.services.audit_service import record_audit_event

HIGH_RISK_GARAGES = {
    "RAPID CASH GARAGE",
    "NATIONAL ACCIDENT REBUILDERS",
    "METRO COLLISION HUB",
}

# Signal weights — the scoring matrix. Tuned so a single strong signal
# (a confirmed duplicate) escalates to INVESTIGATE on its own, while
# weaker signals must accumulate. The total is capped at 100.
WEIGHTS = {
    "duplicate_claim": 40,
    "high_risk_garage": 25,
    "early_claim": 18,
    "inflated_estimate": 16,
    "invalid_licence": 15,
    "repeated_incidents": 14,
    "claim_near_idv": 12,
    "missing_fir_document": 12,
    "late_intimation": 8,
    "policy_near_expiry": 8,
    "insufficient_documents": 6,
    "policy_not_on_file": 6,
}

# Score band cut-offs (on the 0–100 scale).
REVIEW_THRESHOLD = 15
INVESTIGATE_THRESHOLD = 40
CRITICAL_THRESHOLD = 70

# Windows for time-based signals (days).
EARLY_CLAIM_WINDOW = 30
NEAR_EXPIRY_WINDOW = 30
LATE_INTIMATION_DAYS = 7
NEAR_IDV_RATIO = 0.9


def analyze_claim_for_fraud(
    session: Session,
    claim: Claim,
    payload: FraudCheckRequest | None = None,
) -> FraudAnalysisRead:
    """Score a claim against the fraud signal matrix and return a
    recommendation. Pure read-only computation — call
    persist_fraud_assessment to record the result."""
    request = payload or FraudCheckRequest()
    normalized_garage = normalize_garage_name(request.garage_name)

    duplicate_claim_count = find_duplicate_claim_count(session, claim)
    repeated_incident_count = find_repeated_incident_count(session, claim)
    suspicious_repair_cost = is_suspicious_repair_cost(
        claim_amount=float(claim.claim_amount),
        repair_estimate_amount=request.repair_estimate_amount,
    )
    high_risk_garage = (
        normalized_garage in HIGH_RISK_GARAGES if normalized_garage else False
    )

    documents = list(_claim_documents(session, claim.id))
    document_types = {d.document_type for d in documents}
    policy = _policy_for(session, claim.policy_number)

    signals: list[FraudSignal] = []

    # --- Duplicate claim ---
    signals.append(
        _signal(
            "duplicate_claim",
            "Duplicate claim",
            duplicate_claim_count > 0,
            (
                f"{duplicate_claim_count} other claim(s) share this policy, "
                "vehicle and incident date"
                if duplicate_claim_count > 0
                else "No duplicate claims found"
            ),
        )
    )

    # --- High-risk garage ---
    signals.append(
        _signal(
            "high_risk_garage",
            "Flagged repair garage",
            high_risk_garage,
            (
                f"{request.garage_name} is on the high-risk garage list"
                if high_risk_garage
                else "Garage not flagged"
                if normalized_garage
                else "No garage supplied"
            ),
        )
    )

    # --- Early claim (soon after policy inception) ---
    early_claim = False
    if policy is not None:
        days_since_inception = (claim.incident_date - policy.effective_date).days
        early_claim = 0 <= days_since_inception <= EARLY_CLAIM_WINDOW
    signals.append(
        _signal(
            "early_claim",
            "Claim soon after policy start",
            early_claim,
            (
                "Incident occurred within "
                f"{EARLY_CLAIM_WINDOW} days of policy inception"
                if early_claim
                else "Policy not on file"
                if policy is None
                else "Incident well after policy start"
            ),
        )
    )

    # --- Inflated repair estimate ---
    signals.append(
        _signal(
            "inflated_estimate",
            "Inflated repair estimate",
            suspicious_repair_cost,
            (
                "Repair estimate is disproportionately high versus the claim"
                if suspicious_repair_cost
                else "Estimate within expected range"
                if request.repair_estimate_amount
                else "No repair estimate supplied"
            ),
        )
    )

    # --- Invalid driving licence (own-damage / third-party) ---
    invalid_licence = False
    if claim.claim_type in (ClaimType.ACCIDENT, ClaimType.THIRD_PARTY):
        invalid_licence = (
            claim.license_expiry_date is None
            or claim.license_expiry_date < claim.incident_date
        )
    signals.append(
        _signal(
            "invalid_licence",
            "Invalid driving licence",
            invalid_licence,
            (
                "Driving licence missing or expired on the incident date"
                if invalid_licence
                else "Licence valid on the incident date"
            ),
        )
    )

    # --- Repeated incidents ---
    signals.append(
        _signal(
            "repeated_incidents",
            "Repeated incidents",
            repeated_incident_count >= 2,
            (
                f"{repeated_incident_count} prior claims on this vehicle in 90 days"
                if repeated_incident_count >= 2
                else "No unusual incident frequency"
            ),
        )
    )

    # --- Claim near or above IDV ---
    claim_near_idv = claim.idv is not None and float(
        claim.claim_amount
    ) >= NEAR_IDV_RATIO * float(claim.idv)
    signals.append(
        _signal(
            "claim_near_idv",
            "Claim near insured value",
            claim_near_idv,
            (
                "Claimed amount is at or above 90% of the vehicle's IDV"
                if claim_near_idv
                else "Claim comfortably below IDV"
                if claim.idv is not None
                else "No IDV on record"
            ),
        )
    )

    # --- Missing FIR document where one is mandatory ---
    fir_required = claim.claim_type in (ClaimType.THEFT, ClaimType.THIRD_PARTY)
    missing_fir = fir_required and DocumentType.FIR not in document_types
    signals.append(
        _signal(
            "missing_fir_document",
            "Missing FIR document",
            missing_fir,
            (
                "An FIR is mandatory for this claim type but none is uploaded"
                if missing_fir
                else "FIR present or not required"
            ),
        )
    )

    # --- Late intimation ---
    late_intimation = False
    if claim.created_at is not None:
        delay_days = (claim.created_at.date() - claim.incident_date).days
        late_intimation = delay_days > LATE_INTIMATION_DAYS
    signals.append(
        _signal(
            "late_intimation",
            "Late intimation",
            late_intimation,
            (
                f"Filed more than {LATE_INTIMATION_DAYS} days after the incident"
                if late_intimation
                else "Reported promptly"
            ),
        )
    )

    # --- Policy near expiry at incident ---
    policy_near_expiry = False
    if policy is not None:
        days_to_expiry = (policy.expiry_date - claim.incident_date).days
        policy_near_expiry = 0 <= days_to_expiry <= NEAR_EXPIRY_WINDOW
    signals.append(
        _signal(
            "policy_near_expiry",
            "Incident near policy expiry",
            policy_near_expiry,
            (
                f"Incident within {NEAR_EXPIRY_WINDOW} days of policy expiry"
                if policy_near_expiry
                else "Not near expiry"
                if policy is not None
                else "Policy not on file"
            ),
        )
    )

    # --- Insufficient supporting documents ---
    insufficient_documents = len(documents) < 2
    signals.append(
        _signal(
            "insufficient_documents",
            "Insufficient documents",
            insufficient_documents,
            (
                f"Only {len(documents)} document(s) on file"
                if insufficient_documents
                else f"{len(documents)} documents on file"
            ),
        )
    )

    # --- Policy not on file ---
    signals.append(
        _signal(
            "policy_not_on_file",
            "Policy not on file",
            policy is None,
            (
                "No matching policy record was found for screening"
                if policy is None
                else "Policy located"
            ),
        )
    )

    risk_score = min(sum(s.weight for s in signals if s.triggered), 100)
    risk_level = _risk_level(risk_score)
    recommendation = _recommendation(risk_score)
    triggered_rules = [s.code for s in signals if s.triggered]
    summary = _build_summary(recommendation, risk_score, signals)

    return FraudAnalysisRead(
        claim_id=str(claim.id),
        risk_score=risk_score,
        risk_level=risk_level,
        recommendation=recommendation,
        summary=summary,
        signals=signals,
        triggered_rules=triggered_rules,
        duplicate_claim_count=duplicate_claim_count,
        repeated_incident_count=repeated_incident_count,
        suspicious_repair_cost=suspicious_repair_cost,
        high_risk_garage=high_risk_garage,
        garage_name=request.garage_name,
        repair_estimate_amount=request.repair_estimate_amount,
    )


def persist_fraud_assessment(
    session: Session,
    claim: Claim,
    result: FraudAnalysisRead,
) -> FraudAssessment:
    """Record a fraud screening result and emit an audit event."""
    assessment = FraudAssessment(
        claim_id=claim.id,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        recommendation=result.recommendation.value,
        summary=result.summary,
        result=result.model_dump(mode="json"),
    )
    session.add(assessment)
    session.flush()
    record_audit_event(
        session,
        entity_type="fraud_assessment",
        entity_id=str(assessment.id),
        claim_id=claim.id,
        action="FRAUD_ASSESSMENT_RECORDED",
        details={
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "recommendation": result.recommendation.value,
            "triggered_rules": result.triggered_rules,
        },
    )
    session.commit()
    session.refresh(assessment)
    return assessment


def get_latest_assessment(session: Session, claim_id: UUID) -> FraudAssessment | None:
    statement = (
        select(FraudAssessment)
        .where(FraudAssessment.claim_id == claim_id)
        .order_by(FraudAssessment.created_at.desc())
    )
    return session.scalars(statement).first()


def _signal(code: str, label: str, triggered: bool, detail: str) -> FraudSignal:
    return FraudSignal(
        code=code,
        label=label,
        weight=WEIGHTS[code],
        triggered=triggered,
        detail=detail,
    )


def _risk_level(score: int) -> str:
    if score >= CRITICAL_THRESHOLD:
        return "CRITICAL"
    if score >= INVESTIGATE_THRESHOLD:
        return "HIGH"
    if score >= REVIEW_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _recommendation(score: int) -> FraudRecommendation:
    if score >= INVESTIGATE_THRESHOLD:
        return FraudRecommendation.INVESTIGATE
    if score >= REVIEW_THRESHOLD:
        return FraudRecommendation.REVIEW
    return FraudRecommendation.CLEAR


def _build_summary(
    recommendation: FraudRecommendation,
    score: int,
    signals: list[FraudSignal],
) -> str:
    triggered = [s.label for s in signals if s.triggered]
    lead = {
        FraudRecommendation.CLEAR: (
            "Claim appears legitimate. No material fraud indicators."
        ),
        FraudRecommendation.REVIEW: (
            "Some risk indicators present — a manual review is advised "
            "before approval."
        ),
        FraudRecommendation.INVESTIGATE: (
            "Strong fraud indicators — refer to the investigation team "
            "before any payout."
        ),
    }[recommendation]
    if triggered:
        return f"{lead} Risk score {score}/100. Flags: {', '.join(triggered)}."
    return f"{lead} Risk score {score}/100."


def _claim_documents(session: Session, claim_id: UUID):
    # Imported lazily to avoid a circular import at module load.
    from app.services.document_service import list_claim_documents

    return list_claim_documents(session, claim_id)


def _policy_for(session: Session, policy_number: str):
    from app.services.policy_service import get_policy_by_number

    return get_policy_by_number(session, policy_number)


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
