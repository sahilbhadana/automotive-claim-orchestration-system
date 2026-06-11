from uuid import UUID

from fastapi import APIRouter
from fastapi import status

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
from app.api.authz import is_staff
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
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
    payload: ClaimCreate, session: DatabaseSession, current_user: CurrentUser
) -> ClaimRead:
    claim = create_claim(session, payload, claimant_id=current_user.id)
    return ClaimRead.model_validate(claim)


@router.get("", response_model=list[ClaimRead])
async def list_claims_endpoint(
    session: DatabaseSession, current_user: CurrentUser
) -> list[ClaimRead]:
    # Staff see the whole book; customers see only their own claims.
    claimant_filter = None if is_staff(current_user) else current_user.id
    claims = list_claims(session, claimant_id=claimant_filter)
    return [ClaimRead.model_validate(claim) for claim in claims]


@router.get("/{claim_id}", response_model=ClaimRead)
async def get_claim_endpoint(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> ClaimRead:
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))
    return ClaimRead.model_validate(claim)


@router.patch("/{claim_id}/status", response_model=ClaimRead)
async def update_claim_status_endpoint(
    claim_id: UUID,
    payload: ClaimStatusUpdate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> ClaimRead:
    ensure_staff(current_user)
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))
    updated_claim = update_claim_status(session, claim, payload.status)
    return ClaimRead.model_validate(updated_claim)
