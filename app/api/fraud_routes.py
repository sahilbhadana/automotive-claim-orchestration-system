from uuid import UUID

from fastapi import APIRouter

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
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
    # Fraud analysis is an investigative tool, not a customer feature.
    ensure_staff(current_user)
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    return analyze_claim_for_fraud(session, claim, payload)
