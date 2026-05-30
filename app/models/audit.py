from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("claims.id"),
        nullable=True,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    actor: Mapped[str] = mapped_column(String(100), default="system")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
