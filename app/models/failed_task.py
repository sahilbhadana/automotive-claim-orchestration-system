from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class FailedTaskStatus(StrEnum):
    PENDING = "PENDING"
    RETRYING = "RETRYING"
    DEAD = "DEAD"
    RECOVERED = "RECOVERED"


class FailedTask(Base):
    __tablename__ = "failed_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_name: Mapped[str] = mapped_column(String(200), index=True)
    task_args: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_kwargs: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str] = mapped_column(Text)
    error_type: Mapped[str] = mapped_column(String(200))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[FailedTaskStatus] = mapped_column(
        Enum(FailedTaskStatus, name="failed_task_status"),
        default=FailedTaskStatus.PENDING,
        index=True,
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    recovered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
