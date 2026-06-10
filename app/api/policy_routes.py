from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.policy import PolicyCreate
from app.schemas.policy import PolicyRead
from app.schemas.policy import PolicyValidationRequest
from app.schemas.policy import PolicyValidationResult
from app.services.policy_service import create_policy
from app.services.policy_service import get_policy_by_number
from app.services.policy_service import list_policies
from app.services.policy_service import validate_policy_coverage

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("", response_model=PolicyRead, status_code=status.HTTP_201_CREATED)
async def create_policy_endpoint(
    payload: PolicyCreate,
    session: DatabaseSession,
    current_user: CurrentUser
) -> PolicyRead:
    existing_policy = get_policy_by_number(session, payload.policy_number)
    if existing_policy is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy already exists",
        )

    policy = create_policy(session, payload)
    return PolicyRead.model_validate(policy)


@router.get("", response_model=list[PolicyRead])
async def list_policies_endpoint(
    session: DatabaseSession,
    current_user: CurrentUser
) -> list[PolicyRead]:
    policies = list_policies(session)
    return [PolicyRead.model_validate(policy) for policy in policies]


@router.get("/{policy_number}", response_model=PolicyRead)
async def get_policy_endpoint(
    policy_number: str,
    session: DatabaseSession,
    current_user: CurrentUser
) -> PolicyRead:
    policy = get_policy_by_number(session, policy_number)
    if policy is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )
    return PolicyRead.model_validate(policy)


@router.post("/validate", response_model=PolicyValidationResult)
async def validate_policy_endpoint(
    payload: PolicyValidationRequest,
    session: DatabaseSession,
    current_user: CurrentUser
) -> PolicyValidationResult:
    policy = get_policy_by_number(session, payload.policy_number)
    return validate_policy_coverage(policy, payload)


