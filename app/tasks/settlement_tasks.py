from __future__ import annotations

from uuid import UUID

from app.db.session import SessionLocal
from app.services.settlement_service import get_settlement_by_id
from app.services.settlement_service import list_pending_retries
from app.services.settlement_service import process_payout
from app.workers.base_task import ResilientTask
from app.workers.celery_app import celery_app


@celery_app.task(
    name="settlements.process_payout",
    base=ResilientTask,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def process_payout_task(settlement_id: str) -> dict:
    session = SessionLocal()
    try:
        settlement = get_settlement_by_id(session, UUID(settlement_id))
        if settlement is None:
            return {
                "settlement_id": settlement_id,
                "processed": False,
                "error": "Settlement not found",
            }

        updated = process_payout(session, settlement)

        from app.events.publisher import publish_payout_initiated

        if updated.status.value in ("COMPLETED",):
            try:
                publish_payout_initiated(
                    claim_id=updated.claim_id,
                    settlement_id=updated.id,
                    payout_amount=float(updated.payout_amount),
                )
            except Exception:
                pass

        return {
            "settlement_id": settlement_id,
            "processed": True,
            "status": updated.status.value,
            "transaction_reference": updated.transaction_reference,
            "retry_count": updated.retry_count,
        }
    finally:
        session.close()


@celery_app.task(
    name="settlements.retry_pending",
    base=ResilientTask,
)
def retry_pending_payouts_task() -> dict:
    """Periodic task: pick up settlements due for retry and re-process them."""
    session = SessionLocal()
    try:
        pending = list_pending_retries(session)
        dispatched: list[str] = []
        for settlement in pending:
            process_payout_task.delay(str(settlement.id))
            dispatched.append(str(settlement.id))
        return {"dispatched": len(dispatched), "settlement_ids": dispatched}
    finally:
        session.close()
