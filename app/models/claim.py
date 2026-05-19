from __future__ import annotations

import uuid
from datetime import date
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class ClaimStatus(StrEnum):
    CLAIM_CREATED = "CLAIM_CREATED"
    DOCUMENT_VERIFICATION = "DOCUMENT_VERIFICATION"
    POLICY_VALIDATION = "POLICY_VALIDATION"
    FRAUD_ANALYSIS = "FRAUD_ANALYSIS"
    ADJUSTER_ASSIGNMENT = "ADJUSTER_ASSIGNMENT"
    REPAIR_ESTIMATION = "REPAIR_ESTIMATION"
    FINAL_APPROVAL = "FINAL_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAYOUT = "PAYOUT"


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_number: Mapped[str] = mapped_column(String(50), index=True)
    vehicle_number: Mapped[str] = mapped_column(String(20), index=True)
    incident_date: Mapped[date] = mapped_column(Date)
    incident_city: Mapped[str] = mapped_column(String(100))
    claim_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    description: Mapped[str] = mapped_column(String(1000))
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status"),
        default=ClaimStatus.CLAIM_CREATED,
        index=True,
    )
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
