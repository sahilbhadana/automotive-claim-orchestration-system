from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.failed_task import FailedTaskStatus


class FailedTaskRead(BaseModel):
    id: UUID
    task_name: str
    error_message: str
    error_type: str
    retry_count: int
    max_retries: int
    status: FailedTaskStatus
    next_retry_at: datetime | None
    failed_at: datetime
    recovered_at: datetime | None

    model_config = {"from_attributes": True}


class RetryQueueStats(BaseModel):
    total: int
    pending: int
    retrying: int
    dead: int
    recovered: int
