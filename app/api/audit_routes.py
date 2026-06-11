from uuid import UUID

from fastapi import APIRouter

from app.api.authz import ensure_claim_view_access
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.audit import AuditLogRead
from app.services.audit_service import list_claim_audit_events
from app.services.claim_service import get_claim_by_id

router = APIRouter(prefix="/claims/{claim_id}/activity", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
async def list_claim_activity_timeline(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> list[AuditLogRead]:
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    events = list_claim_audit_events(session, claim_id)
    return [AuditLogRead.model_validate(event) for event in events]
