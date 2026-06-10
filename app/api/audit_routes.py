from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.audit import AuditLogRead
from app.services.audit_service import list_claim_audit_events
from app.services.claim_service import get_claim_by_id

router = APIRouter(prefix="/claims/{claim_id}/activity", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
async def list_claim_activity_timeline(
    claim_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser
) -> list[AuditLogRead]:
    claim = get_claim_by_id(session, claim_id)
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found",
        )

    events = list_claim_audit_events(session, claim_id)
    return [AuditLogRead.model_validate(event) for event in events]


