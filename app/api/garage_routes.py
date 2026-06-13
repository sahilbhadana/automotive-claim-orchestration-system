from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.garage import GarageCreate
from app.schemas.garage import GarageRead
from app.schemas.garage import RepairEstimateApprovalRequest
from app.schemas.garage import RepairEstimateCreate
from app.schemas.garage import RepairEstimateRead
from app.services.claim_service import get_claim_by_id
from app.services.garage_service import RepairEstimateWorkflowError
from app.services.garage_service import approve_repair_estimate
from app.services.garage_service import create_garage
from app.services.garage_service import create_repair_estimate
from app.services.garage_service import get_repair_estimate_by_id
from app.services.garage_service import list_claim_repair_estimates
from app.services.garage_service import list_garages

router = APIRouter(tags=["garages"])


@router.post("/garages", response_model=GarageRead, status_code=status.HTTP_201_CREATED)
async def create_garage_endpoint(
    payload: GarageCreate, session: DatabaseSession, current_user: CurrentUser
) -> GarageRead:
    ensure_staff(current_user)
    garage = create_garage(session, payload)
    return GarageRead.model_validate(garage)


@router.get("/garages", response_model=list[GarageRead])
async def list_garages_endpoint(
    session: DatabaseSession, current_user: CurrentUser
) -> list[GarageRead]:
    ensure_staff(current_user)
    garages = list_garages(session)
    return [GarageRead.model_validate(garage) for garage in garages]


@router.post(
    "/claims/{claim_id}/repair-estimates",
    response_model=RepairEstimateRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_repair_estimate_endpoint(
    claim_id: UUID,
    payload: RepairEstimateCreate,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> RepairEstimateRead:
    # Repair estimates are logged by staff against a claim they can see.
    ensure_staff(current_user)
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    try:
        estimate = create_repair_estimate(session, claim, payload)
    except RepairEstimateWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return RepairEstimateRead.model_validate(estimate)


@router.get(
    "/claims/{claim_id}/repair-estimates", response_model=list[RepairEstimateRead]
)
async def list_repair_estimates_endpoint(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> list[RepairEstimateRead]:
    # A claimant may see estimates on their own claim; staff see all.
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    estimates = list_claim_repair_estimates(session, claim_id)
    return [RepairEstimateRead.model_validate(estimate) for estimate in estimates]


@router.post(
    "/repair-estimates/{estimate_id}/approve",
    response_model=RepairEstimateRead,
)
async def approve_repair_estimate_endpoint(
    estimate_id: UUID,
    payload: RepairEstimateApprovalRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> RepairEstimateRead:
    # Approving an estimate authorises spend — staff only.
    ensure_staff(current_user)
    estimate = get_repair_estimate_by_id(session, estimate_id)
    if estimate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repair estimate not found",
        )

    try:
        updated_estimate = approve_repair_estimate(session, estimate, payload)
    except RepairEstimateWorkflowError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return RepairEstimateRead.model_validate(updated_estimate)
