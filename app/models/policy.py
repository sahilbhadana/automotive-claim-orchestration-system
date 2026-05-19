from __future__ import annotations

import uuid
from datetime import date
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class CoverageType(StrEnum):
    THIRD_PARTY = "THIRD_PARTY"
    OWN_DAMAGE = "OWN_DAMAGE"
    COMPREHENSIVE = "COMPREHENSIVE"


class PolicyStatus(StrEnum):
    ACTIVE = "ACTIVE"
    LAPSED = "LAPSED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    insured_name: Mapped[str] = mapped_column(String(120))
    vehicle_number: Mapped[str] = mapped_column(String(20), index=True)
    coverage_type: Mapped[CoverageType] = mapped_column(
        Enum(CoverageType, name="coverage_type"),
        index=True,
    )
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(PolicyStatus, name="policy_status"),
        default=PolicyStatus.ACTIVE,
        index=True,
    )
    effective_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date] = mapped_column(Date)
    is_vehicle_insured: Mapped[bool] = mapped_column(Boolean, default=True)
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
