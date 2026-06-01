from pydantic import BaseModel
from pydantic import Field

from app.models.claim import ClaimStatus


class NotificationDispatchRequest(BaseModel):
    event_name: str = Field(min_length=3, max_length=100)
    message: str | None = Field(default=None, max_length=500)


class NotificationDeliveryRead(BaseModel):
    claim_id: str
    event_name: str
    channels: list[str]
    delivered: bool
    deliveries: list[dict]


class WorkflowNotificationContext(BaseModel):
    previous_status: ClaimStatus | None = None
    current_status: ClaimStatus
    reason: str | None = None
