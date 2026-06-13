from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class SurveyStatus(StrEnum):
    APPOINTED = "APPOINTED"
    INSPECTION_DONE = "INSPECTION_DONE"
    REPORT_SUBMITTED = "REPORT_SUBMITTED"


class InspectionMode(StrEnum):
    PHYSICAL = "PHYSICAL"
    DIGITAL = "DIGITAL"


class SurveyRecommendation(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class Survey(Base):
    """The surveyor lifecycle for one claim: appointment within 24 hours
    of registration, physical or digital inspection before any repairs,
    and a report due within 15 days recommending the payable amount."""

    __tablename__ = "surveys"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id"),
        nullable=False,
        index=True,
    )
    surveyor_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[SurveyStatus] = mapped_column(
        Enum(SurveyStatus, name="survey_status", native_enum=False, length=20),
        default=SurveyStatus.APPOINTED,
        index=True,
    )
    inspection_mode: Mapped[InspectionMode | None] = mapped_column(
        Enum(InspectionMode, name="inspection_mode", native_enum=False, length=20),
        nullable=True,
    )
    inspection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_loss_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    recommended_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    recommendation: Mapped[SurveyRecommendation | None] = mapped_column(
        Enum(
            SurveyRecommendation,
            name="survey_recommendation",
            native_enum=False,
            length=20,
        ),
        nullable=True,
    )
    report_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    appointed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    inspected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    report_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Regulatory TAT: survey report due within 15 days of appointment.
    report_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
