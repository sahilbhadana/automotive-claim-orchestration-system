from pydantic import BaseModel
from pydantic import Field

from app.models.claim import ClaimStatus


class WorkflowStateRead(BaseModel):
    claim_id: str
    current_status: ClaimStatus
    allowed_transitions: list[ClaimStatus]
    terminal: bool


class WorkflowStepExecutionRequest(BaseModel):
    target_status: ClaimStatus | None = None
    reason: str | None = Field(default=None, max_length=500)


class WorkflowExecutionRead(BaseModel):
    claim_id: str
    previous_status: ClaimStatus
    current_status: ClaimStatus
    executed_transition: str
    allowed_next_transitions: list[ClaimStatus]
    terminal: bool
    reason: str | None = None
