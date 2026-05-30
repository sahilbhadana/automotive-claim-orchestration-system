from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class RepairEstimateStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RepairEstimate(Base):
    __tablename__ = "repair_estimates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id"), index=True)
    garage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("garages.id"), index=True)
    estimated_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    notes: Mapped[str] = mapped_column(String(1000))
    status: Mapped[RepairEstimateStatus] = mapped_column(
        Enum(RepairEstimateStatus, name="repair_estimate_status"),
        default=RepairEstimateStatus.SUBMITTED,
        index=True,
    )
    approval_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
