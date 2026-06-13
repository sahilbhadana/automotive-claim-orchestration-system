from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class FraudAssessment(Base):
    """A persisted fraud screening result for a claim. Each run is stored
    so the recommendation that informed an approval is on the record and
    auditable; the latest row is the current assessment."""

    __tablename__ = "fraud_assessments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id"),
        nullable=False,
        index=True,
    )
    risk_score: Mapped[int] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(20), index=True)
    recommendation: Mapped[str] = mapped_column(String(20), index=True)
    summary: Mapped[str] = mapped_column(String(1000))
    # The full FraudAnalysisRead payload (signals matrix included).
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
