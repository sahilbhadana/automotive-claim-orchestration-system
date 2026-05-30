from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class AdjusterExpertise(StrEnum):
    MOTOR_GENERAL = "MOTOR_GENERAL"
    HIGH_VALUE = "HIGH_VALUE"
    FRAUD_SENSITIVE = "FRAUD_SENSITIVE"


class Adjuster(Base):
    __tablename__ = "adjusters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(100), index=True)
    expertise: Mapped[AdjusterExpertise] = mapped_column(
        Enum(AdjusterExpertise, name="adjuster_expertise"),
        index=True,
    )
    max_active_claims: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
