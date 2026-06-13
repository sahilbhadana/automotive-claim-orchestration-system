from uuid import UUID

from celery.result import AsyncResult
from fastapi import APIRouter
from fastapi import status

from app.api.authz import ensure_claim_view_access
from app.api.authz import ensure_staff
from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.schemas.fraud import FraudCheckRequest
from app.schemas.notification import NotificationDispatchRequest
from app.schemas.task import RepairEstimateApprovalTaskRequest
from app.schemas.task import AsyncWorkflowExecutionRequest
from app.schemas.task import TaskDispatchRead
from app.schemas.task import TaskStatusRead
from app.services.claim_service import get_claim_by_id
from app.tasks.claim_tasks import assign_adjuster_task
from app.tasks.claim_tasks import approve_repair_estimate_task
from app.tasks.claim_tasks import execute_workflow_step_task
from app.tasks.claim_tasks import run_claim_fraud_checks_task
from app.tasks.claim_tasks import send_claim_notification_task
from app.tasks.claim_tasks import validate_claim_images_task
from app.workers.celery_app import celery_app

router = APIRouter(tags=["tasks"])


@router.post(
    "/claims/{claim_id}/workflow/execute-async",
    response_model=TaskDispatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch_async_workflow_execution(
    claim_id: UUID,
    payload: AsyncWorkflowExecutionRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> TaskDispatchRead:
    # Mirror the synchronous workflow guard: staff-only, own claim only.
    ensure_staff(current_user)
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    task = execute_workflow_step_task.delay(
        str(claim_id),
        payload.target_status.value if payload.target_status else None,
        payload.reason,
    )
    return TaskDispatchRead(task_id=task.id, task_name=task.task, status=task.status)


@router.post(
    "/claims/{claim_id}/tasks/image-validation",
    response_model=TaskDispatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch_image_validation_task(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> TaskDispatchRead:
    ensure_staff(current_user)
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    task = validate_claim_images_task.delay(str(claim_id))
    return TaskDispatchRead(task_id=task.id, task_name=task.task, status=task.status)


@router.post(
    "/claims/{claim_id}/tasks/fraud-check",
    response_model=TaskDispatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch_fraud_check_task(
    claim_id: UUID,
    payload: FraudCheckRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> TaskDispatchRead:
    ensure_staff(current_user)
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    task = run_claim_fraud_checks_task.delay(
        str(claim_id),
        payload.garage_name,
        payload.repair_estimate_amount,
    )
    return TaskDispatchRead(task_id=task.id, task_name=task.task, status=task.status)


@router.post(
    "/claims/{claim_id}/tasks/assign-adjuster",
    response_model=TaskDispatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch_adjuster_assignment_task(
    claim_id: UUID, session: DatabaseSession, current_user: CurrentUser
) -> TaskDispatchRead:
    ensure_staff(current_user)
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    task = assign_adjuster_task.delay(str(claim_id))
    return TaskDispatchRead(task_id=task.id, task_name=task.task, status=task.status)


@router.post(
    "/repair-estimates/{estimate_id}/approve-async",
    response_model=TaskDispatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch_repair_estimate_approval_task(
    estimate_id: UUID,
    payload: RepairEstimateApprovalTaskRequest,
    current_user: CurrentUser,
) -> TaskDispatchRead:
    # Approving an estimate authorises spend — staff only.
    ensure_staff(current_user)
    task = approve_repair_estimate_task.delay(
        str(estimate_id),
        payload.approved,
        payload.approval_notes,
    )
    return TaskDispatchRead(task_id=task.id, task_name=task.task, status=task.status)


@router.post(
    "/claims/{claim_id}/tasks/notifications",
    response_model=TaskDispatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def dispatch_notification_task(
    claim_id: UUID,
    payload: NotificationDispatchRequest,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> TaskDispatchRead:
    ensure_staff(current_user)
    ensure_claim_view_access(current_user, get_claim_by_id(session, claim_id))

    task = send_claim_notification_task.delay(
        str(claim_id),
        payload.event_name,
        payload.message,
    )
    return TaskDispatchRead(task_id=task.id, task_name=task.task, status=task.status)


@router.get("/tasks/{task_id}", response_model=TaskStatusRead)
async def get_background_task_status(
    task_id: str, current_user: CurrentUser
) -> TaskStatusRead:
    # Task results can contain claim data; keep polling staff-only.
    ensure_staff(current_user)
    result = AsyncResult(task_id, app=celery_app)
    payload = result.result if isinstance(result.result, dict) else None
    return TaskStatusRead(
        task_id=task_id,
        status=result.status,
        task_name=None,
        result=payload,
    )
