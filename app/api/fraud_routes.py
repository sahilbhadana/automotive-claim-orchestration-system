from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.fraud import FraudAnalysisRead
from app.schemas.fraud import FraudCheckRequest
from app.services.claim_service import get_claim_by_id
from app.services.fraud_service import analyze_claim_for_fraud

router = APIRouter(prefix="/claims/{claim_id}/fraud", tags=["fraud"])


@router.post("/analyze", response_model=FraudAnalysisRead)
async def analyze_claim_for_fraud_endpoint(
    claim_id: UUID,
    payload: FraudCheckRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> FraudAnalysisRead:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    return analyze_claim_for_fraud(session, claim, payload)
