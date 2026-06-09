from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from typing import Generator

from app.core.config import settings
from app.events.event_schemas import BaseEvent

logger = logging.getLogger(__name__)

_EXCHANGE_NAME = "insurance.claims"
_CONNECTION_PARAMS: dict | None = None


def _get_connection_params() -> dict | None:
    amqp_url = getattr(settings, "amqp_url", None)
    if not amqp_url:
        return None
    return {"url": amqp_url}


@contextmanager
def _open_channel() -> Generator:
    """Open a blocking pika channel; yields None when AMQP is not configured."""
    params = _get_connection_params()
    if params is None:
        yield None
        return

    try:
        import pika  # type: ignore[import]

        connection = pika.BlockingConnection(pika.URLParameters(params["url"]))
        channel = connection.channel()
        channel.exchange_declare(
            exchange=_EXCHANGE_NAME,
            exchange_type="topic",
            durable=True,
        )
        try:
            yield channel
        finally:
            connection.close()
    except Exception as exc:
        logger.warning("RabbitMQ unavailable, event not published: %s", exc)
        yield None


def publish_event(event: BaseEvent, routing_key: str | None = None) -> bool:
    """Publish a domain event to RabbitMQ.

    Returns True when the message was delivered, False when AMQP is not
    reachable (the caller should not treat this as a hard failure).
    """
    key = routing_key or event.event_type.value.lower().replace(".", "_")
    body = event.model_dump_json().encode()

    with _open_channel() as channel:
        if channel is None:
            logger.info(
                "Event published (log-only fallback): type=%s key=%s payload=%s",
                event.event_type,
                key,
                event.payload,
            )
            return False

        try:
            import pika  # type: ignore[import]

            channel.basic_publish(
                exchange=_EXCHANGE_NAME,
                routing_key=key,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                    headers={"correlation_id": event.correlation_id},
                ),
            )
            logger.debug("Event published: type=%s key=%s", event.event_type, key)
            return True
        except Exception as exc:
            logger.error("Failed to publish event: %s", exc)
            return False


def publish_claim_created(
    claim_id,
    policy_number: str,
    vehicle_number: str,
    claim_amount: float,
    incident_city: str,
    correlation_id: str | None = None,
) -> bool:
    from app.events.event_schemas import ClaimCreatedEvent

    event = ClaimCreatedEvent.build(
        claim_id=claim_id,
        policy_number=policy_number,
        vehicle_number=vehicle_number,
        claim_amount=claim_amount,
        incident_city=incident_city,
        correlation_id=correlation_id,
    )
    return publish_event(event, routing_key="claim.created")


def publish_fraud_check_completed(
    claim_id,
    risk_level: str,
    risk_score: int,
    triggered_rules: list[str],
    correlation_id: str | None = None,
) -> bool:
    from app.events.event_schemas import FraudCheckCompletedEvent

    event = FraudCheckCompletedEvent.build(
        claim_id=claim_id,
        risk_level=risk_level,
        risk_score=risk_score,
        triggered_rules=triggered_rules,
        correlation_id=correlation_id,
    )
    return publish_event(event, routing_key="claim.fraud.completed")


def publish_claim_approved(
    claim_id,
    policy_number: str,
    claim_amount: float,
    adjuster_id=None,
    correlation_id: str | None = None,
) -> bool:
    from app.events.event_schemas import ClaimApprovedEvent

    event = ClaimApprovedEvent.build(
        claim_id=claim_id,
        policy_number=policy_number,
        claim_amount=claim_amount,
        adjuster_id=adjuster_id,
        correlation_id=correlation_id,
    )
    return publish_event(event, routing_key="claim.approved")


def publish_payout_initiated(
    claim_id,
    settlement_id,
    payout_amount: float,
    correlation_id: str | None = None,
) -> bool:
    from app.events.event_schemas import PayoutInitiatedEvent

    event = PayoutInitiatedEvent.build(
        claim_id=claim_id,
        settlement_id=settlement_id,
        payout_amount=payout_amount,
        correlation_id=correlation_id,
    )
    return publish_event(event, routing_key="claim.payout.initiated")
