from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.adjuster import AdjusterAssignmentRead
from app.schemas.adjuster import AdjusterCreate
from app.schemas.adjuster import AdjusterRead
from app.services.adjuster_service import AdjusterAssignmentError
from app.services.adjuster_service import assign_best_adjuster
from app.services.adjuster_service import create_adjuster
from app.services.adjuster_service import determine_required_expertise
from app.services.adjuster_service import get_pending_workload_count
from app.services.adjuster_service import list_adjusters
from app.services.claim_service import get_claim_by_id

router = APIRouter(tags=["adjusters"])


@router.post(
    "/adjusters",
    response_model=AdjusterRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_adjuster_endpoint(
    payload: AdjusterCreate, session: DatabaseSession, current_user: CurrentUser
) -> AdjusterRead:
    ensure_staff(current_user)
    adjuster = create_adjuster(
        session=session,
        full_name=payload.full_name,
        city=payload.city,
        expertise=payload.expertise,
        max_active_claims=payload.max_active_claims,
        is_active=payload.is_active,
    )
    return AdjusterRead.model_validate(adjuster)


@router.get("/adjusters", response_model=list[AdjusterRead])
async def list_adjusters_endpoint(
    session: DatabaseSession, current_user: CurrentUser
) -> list[AdjusterRead]:
    ensure_staff(current_user)
    adjusters = list_adjusters(session)
    return [AdjusterRead.model_validate(adjuster) for adjuster in adjusters]


@router.post(
    "/claims/{claim_id}/adjuster/assign",
    response_model=AdjusterAssignmentRead,
)
async def assign_adjuster_endpoint(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> AdjusterAssignmentRead:
    ensure_staff(current_user)
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    try:
        ranked = assign_best_adjuster(session, claim)
    except AdjusterAssignmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return AdjusterAssignmentRead(
        claim_id=claim.id,
        adjuster_id=ranked.adjuster.id,
        adjuster_name=ranked.adjuster.full_name,
        city_match=ranked.city_match,
        workload_count=get_pending_workload_count(session, ranked.adjuster.id),
        max_active_claims=ranked.adjuster.max_active_claims,
        required_expertise=determine_required_expertise(float(claim.claim_amount)),
        assigned_expertise=ranked.adjuster.expertise,
    )
