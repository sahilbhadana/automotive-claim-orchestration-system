from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.workflow import WorkflowExecutionRead
from app.schemas.workflow import WorkflowStateRead
from app.schemas.workflow import WorkflowStepExecutionRequest
from app.services.claim_service import get_claim_by_id
from app.services.workflow_service import WorkflowTransitionError
from app.services.workflow_service import build_workflow_transition_name
from app.services.workflow_service import execute_workflow_step
from app.services.workflow_service import get_allowed_transitions
from app.services.workflow_service import is_terminal_state
from app.services.workflow_service import serialize_claim_id

router = APIRouter(prefix="/claims/{claim_id}/workflow", tags=["workflow"])


@router.get("", response_model=WorkflowStateRead)
async def get_claim_workflow_state(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> WorkflowStateRead:
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    amount = float(claim.claim_amount)
    return WorkflowStateRead(
        claim_id=serialize_claim_id(claim.id),
        current_status=claim.status,
        allowed_transitions=get_allowed_transitions(
            claim.status, claim.claim_type, amount
        ),
        terminal=is_terminal_state(claim.status, claim.claim_type, amount),
    )


@router.post("/execute", response_model=WorkflowExecutionRead)
async def execute_claim_workflow_step(
    claim_id: UUID,
    payload: WorkflowStepExecutionRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> WorkflowExecutionRead:
    # Workflow transitions are operational decisions: staff only.
    ensure_staff(current_user)
    claim = ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    try:
        previous_status, updated_claim = execute_workflow_step(
            session=session,
            claim=claim,
            target_status=payload.target_status,
        )
    except WorkflowTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return WorkflowExecutionRead(
        claim_id=serialize_claim_id(updated_claim.id),
        previous_status=previous_status,
        current_status=updated_claim.status,
        executed_transition=build_workflow_transition_name(
            previous_status=previous_status,
            current_status=updated_claim.status,
        ),
        allowed_next_transitions=get_allowed_transitions(
            updated_claim.status,
            updated_claim.claim_type,
            float(updated_claim.claim_amount),
        ),
        terminal=is_terminal_state(
            updated_claim.status,
            updated_claim.claim_type,
            float(updated_claim.claim_amount),
        ),
        reason=payload.reason,
    )
