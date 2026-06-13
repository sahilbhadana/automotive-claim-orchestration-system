from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.models.survey import Survey
from app.schemas.survey import SurveyAppointRequest
from app.schemas.survey import SurveyInspectionRequest
from app.schemas.survey import SurveyRead
from app.schemas.survey import SurveyReportRequest
from app.services.claim_service import get_claim_by_id
from app.services.survey_service import SurveyError
from app.services.survey_service import appoint_surveyor
from app.services.survey_service import get_survey_for_claim
from app.services.survey_service import is_report_overdue
from app.services.survey_service import record_inspection
from app.services.survey_service import submit_survey_report

router = APIRouter(prefix="/claims/{claim_id}/survey", tags=["survey"])


def _serialize(survey: Survey) -> SurveyRead:
    data = SurveyRead.model_validate(survey)
    data.report_overdue = is_report_overdue(survey)
    return data


@router.get("", response_model=SurveyRead)
async def get_claim_survey(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> SurveyRead:
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))
    survey = get_survey_for_claim(session, claim_id)
    if survey is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No surveyor has been appointed for this claim",
        )
    return _serialize(survey)


@router.post("/appoint", response_model=SurveyRead, status_code=201)
async def appoint_claim_surveyor(
    claim_id: UUID,
    payload: SurveyAppointRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> SurveyRead:
    ensure_staff(current_user)
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))
    try:
        survey = appoint_surveyor(session, claim, payload.surveyor_name)
    except SurveyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize(survey)


@router.post("/inspection", response_model=SurveyRead)
async def record_claim_inspection(
    claim_id: UUID,
    payload: SurveyInspectionRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> SurveyRead:
    ensure_staff(current_user)
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))
    survey = get_survey_for_claim(session, claim_id)
    if survey is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A surveyor must be appointed before recording an inspection",
        )
    try:
        survey = record_inspection(
            session, survey, payload.inspection_mode, payload.notes
        )
    except SurveyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize(survey)


@router.post("/report", response_model=SurveyRead)
async def submit_claim_survey_report(
    claim_id: UUID,
    payload: SurveyReportRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> SurveyRead:
    ensure_staff(current_user)
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))
    survey = get_survey_for_claim(session, claim_id)
    if survey is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A surveyor must be appointed before a report can be submitted",
        )
    try:
        survey = submit_survey_report(
            session,
            survey,
            estimated_loss_amount=payload.estimated_loss_amount,
            recommended_amount=payload.recommended_amount,
            recommendation=payload.recommendation,
            notes=payload.notes,
        )
    except SurveyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize(survey)
