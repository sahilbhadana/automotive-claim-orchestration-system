from uuid import UUID

from fastapi import APIRouter
from fastapi import HTTPException

from app.api.dependencies import CurrentUser
from app.api.dependencies import DatabaseSession
from app.models.failed_task import FailedTaskStatus
from app.models.user import UserRole  # noqa: F401 - used in role checks
from app.schemas.retry import FailedTaskRead
from app.schemas.retry import RetryQueueStats
from app.services.retry_service import dismiss_failed_task
from app.services.retry_service import get_failed_task_by_id
from app.services.retry_service import list_dead_letter_queue
from app.services.retry_service import list_failed_tasks
from app.services.retry_service import requeue_failed_task
from app.services.retry_service import schedule_retry

router = APIRouter(prefix="/dlq", tags=["Dead-Letter Queue"])


@router.get("", response_model=list[FailedTaskRead])
def get_dead_letter_queue(
    session: DatabaseSession,
    current_user: CurrentUser,
) -> list[FailedTaskRead]:
    if current_user.role not in (UserRole.ADMIN,):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return list_dead_letter_queue(session)


@router.get("/all", response_model=list[FailedTaskRead])
def get_all_failed_tasks(
    session: DatabaseSession,
    *,
    status: FailedTaskStatus | None = None,
    current_user: CurrentUser,
) -> list[FailedTaskRead]:
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPERVISOR):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return list_failed_tasks(session, status=status)


@router.get("/stats", response_model=RetryQueueStats)
def get_retry_queue_stats(
    session: DatabaseSession,
    current_user: CurrentUser,
) -> RetryQueueStats:
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPERVISOR):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    all_tasks = list_failed_tasks(session)
    return RetryQueueStats(
        total=len(all_tasks),
        pending=sum(1 for t in all_tasks if t.status == FailedTaskStatus.PENDING),
        retrying=sum(1 for t in all_tasks if t.status == FailedTaskStatus.RETRYING),
        dead=sum(1 for t in all_tasks if t.status == FailedTaskStatus.DEAD),
        recovered=sum(1 for t in all_tasks if t.status == FailedTaskStatus.RECOVERED),
    )


@router.post("/{task_id}/retry", response_model=FailedTaskRead)
def requeue_task(
    task_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> FailedTaskRead:
    if current_user.role not in (UserRole.ADMIN,):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    task = requeue_failed_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Failed task not found")
    return task


@router.post("/{task_id}/schedule-retry", response_model=FailedTaskRead)
def trigger_exponential_retry(
    task_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> FailedTaskRead:
    if current_user.role not in (UserRole.ADMIN,):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    task = get_failed_task_by_id(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Failed task not found")
    return schedule_retry(session, task)


@router.delete("/{task_id}")
def dismiss_task_from_queue(
    task_id: UUID,
    session: DatabaseSession,
    current_user: CurrentUser,
) -> dict:
    if current_user.role not in (UserRole.ADMIN,):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    deleted = dismiss_failed_task(session, task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Failed task not found")
    return {"deleted": True, "task_id": str(task_id)}

