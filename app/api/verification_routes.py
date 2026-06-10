from fastapi import APIRouter

from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.verification import VerificationRequest
from app.schemas.verification import VerificationResult
from app.services.policy_service import get_policy_by_number
from app.services.verification_service import verify_vehicle_and_driver

router = APIRouter(prefix="/verifications", tags=["verifications"])


@router.post("/vehicle-driver", response_model=VerificationResult)
async def verify_vehicle_and_driver_endpoint(
    payload: VerificationRequest, session: DatabaseSession, current_user: CurrentUser
) -> VerificationResult:
    policy = get_policy_by_number(session, payload.policy_number)
    return verify_vehicle_and_driver(policy, payload)
