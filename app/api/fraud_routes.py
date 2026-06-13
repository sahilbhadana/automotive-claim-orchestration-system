from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.fraud import FraudAnalysisRead
from app.schemas.fraud import FraudCheckRequest
from app.services.claim_service import get_claim_by_id
from app.services.fraud_service import analyze_claim_for_fraud
from app.services.fraud_service import get_latest_assessment
from app.services.fraud_service import persist_fraud_assessment

router = APIRouter(prefix="/claims/{claim_id}/fraud", tags=["fraud"])


@router.post("/analyze", response_model=FraudAnalysisRead)
async def analyze_claim_for_fraud_endpoint(
    claim_id: UUID,
    payload: FraudCheckRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> FraudAnalysisRead:
    # Fraud analysis is an investigative tool, not a customer feature.
    ensure_staff(current_user)
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    result = analyze_claim_for_fraud(session, claim, payload)
    persist_fraud_assessment(session, claim, result)
    return result


@router.get("", response_model=FraudAnalysisRead)
async def get_latest_fraud_assessment(
    claim_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> FraudAnalysisRead:
    """Return the most recent stored fraud assessment for the claim."""
    ensure_staff(current_user)
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    assessment = get_latest_assessment(session, claim_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fraud assessment has been run for this claim",
        )
    return FraudAnalysisRead.model_validate(assessment.result)
