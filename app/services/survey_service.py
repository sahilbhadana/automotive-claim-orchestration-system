from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from datetime import timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.survey import InspectionMode
from app.models.survey import Survey
from app.models.survey import SurveyRecommendation
from app.models.survey import SurveyStatus
from app.services.audit_service import record_audit_event

# Regulatory turnaround time: survey report due within 15 days of
# the surveyor's appointment.
SURVEY_REPORT_TAT_DAYS = 15

# A vehicle is treated as a total loss when the assessed repair cost
# reaches this fraction of its Insured Declared Value.
TOTAL_LOSS_THRESHOLD = 0.75


class SurveyError(ValueError):
    pass


def get_survey_for_claim(session: Session, claim_id: UUID) -> Survey | None:
    statement = (
        select(Survey)
        .where(Survey.claim_id == claim_id)
        .order_by(Survey.appointed_at.desc())
    )
    return session.scalars(statement).first()


def appoint_surveyor(
    session: Session,
    claim: Claim,
    surveyor_name: str,
) -> Survey:
    existing = get_survey_for_claim(session, claim.id)
    if existing is not None:
        raise SurveyError("A surveyor is already appointed for this claim")

    now = datetime.now(tz=timezone.utc)
    survey = Survey(
        claim_id=claim.id,
        surveyor_name=surveyor_name,
        status=SurveyStatus.APPOINTED,
        appointed_at=now,
        report_due_at=now + timedelta(days=SURVEY_REPORT_TAT_DAYS),
    )
    session.add(survey)
    session.flush()
    record_audit_event(
        session,
        entity_type="survey",
        entity_id=str(survey.id),
        claim_id=claim.id,
        action="SURVEYOR_APPOINTED",
        details={
            "surveyor_name": surveyor_name,
            "report_due_at": survey.report_due_at.isoformat(),
        },
    )
    session.commit()
    session.refresh(survey)
    return survey


def record_inspection(
    session: Session,
    survey: Survey,
    inspection_mode: InspectionMode,
    notes: str | None = None,
) -> Survey:
    if survey.status == SurveyStatus.REPORT_SUBMITTED:
        raise SurveyError("Survey report already submitted; inspection is closed")

    survey.inspection_mode = inspection_mode
    survey.inspection_notes = notes
    survey.inspected_at = datetime.now(tz=timezone.utc)
    survey.status = SurveyStatus.INSPECTION_DONE
    record_audit_event(
        session,
        entity_type="survey",
        entity_id=str(survey.id),
        claim_id=survey.claim_id,
        action="VEHICLE_INSPECTED",
        details={
            "inspection_mode": inspection_mode.value,
            "notes": notes,
        },
    )
    session.commit()
    session.refresh(survey)
    return survey


def submit_survey_report(
    session: Session,
    survey: Survey,
    estimated_loss_amount: float,
    recommended_amount: float,
    recommendation: SurveyRecommendation,
    notes: str | None = None,
) -> Survey:
    if survey.inspected_at is None:
        raise SurveyError(
            "Vehicle inspection must be completed before the report is submitted"
        )
    if survey.status == SurveyStatus.REPORT_SUBMITTED:
        raise SurveyError("Survey report already submitted")
    if recommended_amount > estimated_loss_amount:
        raise SurveyError("Recommended amount cannot exceed the estimated loss amount")

    survey.estimated_loss_amount = estimated_loss_amount
    survey.recommended_amount = recommended_amount
    survey.recommendation = recommendation
    survey.report_notes = notes
    survey.report_submitted_at = datetime.now(tz=timezone.utc)
    survey.status = SurveyStatus.REPORT_SUBMITTED

    # Total-loss check: repair cost reaching 75% of IDV is settled as a
    # total loss at IDV rather than repaired.
    claim = session.get(Claim, survey.claim_id)
    total_loss = bool(
        claim is not None
        and claim.idv is not None
        and estimated_loss_amount >= TOTAL_LOSS_THRESHOLD * float(claim.idv)
    )
    survey.total_loss_flagged = total_loss

    record_audit_event(
        session,
        entity_type="survey",
        entity_id=str(survey.id),
        claim_id=survey.claim_id,
        action="SURVEY_REPORT_SUBMITTED",
        details={
            "estimated_loss_amount": float(estimated_loss_amount),
            "recommended_amount": float(recommended_amount),
            "recommendation": recommendation.value,
            "total_loss_flagged": total_loss,
        },
    )
    session.commit()
    session.refresh(survey)
    return survey


def is_report_overdue(survey: Survey) -> bool:
    if survey.report_submitted_at is not None or survey.report_due_at is None:
        return False
    due = survey.report_due_at
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc) > due
