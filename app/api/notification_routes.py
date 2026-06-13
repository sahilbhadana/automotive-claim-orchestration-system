from uuid import UUID

from fastapi import APIRouter
from fastapi import status

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.notification import NotificationDeliveryRead
from app.schemas.notification import NotificationDispatchRequest
from app.services.claim_service import get_claim_by_id
from app.services.notification_service import dispatch_claim_notification

router = APIRouter(prefix="/claims/{claim_id}/notifications", tags=["notifications"])


@router.post(
    "/dispatch",
    response_model=NotificationDeliveryRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch_claim_notification_endpoint(
    claim_id: UUID,
    payload: NotificationDispatchRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> NotificationDeliveryRead:
    # Manual notification dispatch is an operational action for staff.
    ensure_staff(current_user)
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    result = dispatch_claim_notification(
        session=session,
        claim=claim,
        event_name=payload.event_name,
        override_message=payload.message,
    )
    return NotificationDeliveryRead(**result)
