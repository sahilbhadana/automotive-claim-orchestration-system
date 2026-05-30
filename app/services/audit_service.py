from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit_event(
    session: Session,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    claim_id: UUID | None = None,
    actor: str = "system",
    details: dict | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        claim_id=claim_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        details=details or {},
    )
    session.add(audit_log)
    return audit_log


def list_claim_audit_events(session: Session, claim_id: UUID) -> list[AuditLog]:
    statement = (
        select(AuditLog)
        .where(AuditLog.claim_id == claim_id)
        .order_by(AuditLog.created_at.desc())
    )
    return list(session.scalars(statement).all())
