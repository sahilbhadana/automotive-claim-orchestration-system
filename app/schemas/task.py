from pydantic import BaseModel
from pydantic import Field

from app.models.claim import ClaimStatus


class TaskDispatchRead(BaseModel):
    task_id: str
    task_name: str
    status: str


class NotificationTaskRequest(BaseModel):
    message: str = Field(min_length=3, max_length=500)


class RepairEstimateApprovalTaskRequest(BaseModel):
    approved: bool
    approval_notes: str | None = Field(default=None, max_length=500)


class TaskStatusRead(BaseModel):
    task_id: str
    status: str
    task_name: str | None = None
    result: dict | None = None


class AsyncWorkflowExecutionRequest(BaseModel):
    target_status: ClaimStatus | None = None
    reason: str | None = Field(default=None, max_length=500)
