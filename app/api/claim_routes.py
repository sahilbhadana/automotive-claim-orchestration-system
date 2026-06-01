from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.api.dependencies import require_roles
from app.models.user import UserRole
from app.schemas.claim import ClaimCreate
from app.schemas.claim import ClaimRead
from app.schemas.claim import ClaimStatusUpdate
from app.services.claim_service import create_claim
from app.services.claim_service import get_claim_by_id
from app.services.claim_service import list_claims
from app.services.claim_service import update_claim_status

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("", response_model=ClaimRead, status_code=status.HTTP_201_CREATED)
async def create_claim_endpoint(
    payload: ClaimCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ClaimRead:
    claim = create_claim(session, payload)
    return ClaimRead.model_validate(claim)


@router.get("", response_model=list[ClaimRead])
async def list_claims_endpoint(
    session: DatabaseSession,
    current_user: CurrentUser,
) -> list[ClaimRead]:
    claims = list_claims(session)
    return [ClaimRead.model_validate(claim) for claim in claims]


@router.get("/{claim_id}", response_model=ClaimRead)
async def get_claim_endpoint(
    claim_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ClaimRead:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    return ClaimRead.model_validate(claim)


@router.patch("/{claim_id}/status", response_model=ClaimRead)
async def update_claim_status_endpoint(
    claim_id: UUID,
    payload: ClaimStatusUpdate,
    session: DatabaseSession,
    current_user: CurrentUser = require_roles(
        UserRole.ADJUSTER,
        UserRole.SUPERVISOR,
        UserRole.ADMIN,
    ),
) -> ClaimRead:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )
    updated_claim = update_claim_status(session, claim, payload.status)
    return ClaimRead.model_validate(updated_claim)
