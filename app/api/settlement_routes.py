from uuid import UUID

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException

from app.api.dependencies import DatabaseSession
from app.api.dependencies import require_roles
from app.models.user import UserRole
from app.schemas.settlement import InitiatePayoutRequest
from app.schemas.settlement import SettlementRead
from app.services.claim_service import get_claim_by_id
from app.services.settlement_service import get_settlement_by_id
from app.services.settlement_service import initiate_payout
from app.services.settlement_service import list_settlements_for_claim
from app.services.settlement_service import reverse_settlement
from app.tasks.settlement_tasks import process_payout_task

router = APIRouter(tags=["Settlements & Payouts"])


@router.post(
    "/claims/{claim_id}/settlements",
    response_model=SettlementRead,
    status_code=201,
)
def initiate_claim_payout(
    claim_id: UUID,
    payload: InitiatePayoutRequest,
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
    _=require_roles(UserRole.ADMIN, UserRole.SUPERVISOR),
) -> SettlementRead:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    settlement = initiate_payout(session, claim, payload)
    background_tasks.add_task(process_payout_task.delay, str(settlement.id))
    return settlement


@router.get(
    "/claims/{claim_id}/settlements",
    response_model=list[SettlementRead],
)
def list_claim_settlements(
    claim_id: UUID,
    session: DatabaseSession,
    _=require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ADJUSTER),
) -> list[SettlementRead]:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return list_settlements_for_claim(session, claim_id)


@router.get(
    "/settlements/{settlement_id}",
    response_model=SettlementRead,
)
def get_settlement(
    settlement_id: UUID,
    session: DatabaseSession,
    _=require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ADJUSTER),
) -> SettlementRead:
    settlement = get_settlement_by_id(session, settlement_id)
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return settlement


@router.post(
    "/settlements/{settlement_id}/retry",
    response_model=SettlementRead,
)
def retry_failed_settlement(
    settlement_id: UUID,
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
    _=require_roles(UserRole.ADMIN),
) -> SettlementRead:
    settlement = get_settlement_by_id(session, settlement_id)
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")

    background_tasks.add_task(process_payout_task.delay, str(settlement_id))
    return settlement


@router.post(
    "/settlements/{settlement_id}/reverse",
    response_model=SettlementRead,
)
def reverse_completed_settlement(
    settlement_id: UUID,
    reason: str,
    session: DatabaseSession,
    _=require_roles(UserRole.ADMIN),
) -> SettlementRead:
    settlement = get_settlement_by_id(session, settlement_id)
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    return reverse_settlement(session, settlement, reason)
