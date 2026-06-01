from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.claim import ClaimStatus
from app.services.audit_service import record_audit_event


@dataclass(frozen=True)
class NotificationTemplate:
    key: str
    subject: str
    email_body: str
    sms_body: str


@dataclass(frozen=True)
class NotificationPayload:
    channel: str
    recipient: str
    subject: str | None
    content: str


TEMPLATES: dict[str, NotificationTemplate] = {
    "claim_created": NotificationTemplate(
        key="claim_created",
        subject="Claim registered: {claim_id}",
        email_body=(
            "Your automotive claim {claim_id} has been created for policy {policy_number}. "
            "Current status: {current_status}."
        ),
        sms_body="Claim {claim_id} created. Status: {current_status}.",
    ),
    "workflow_transition": NotificationTemplate(
        key="workflow_transition",
        subject="Claim update: {claim_id} moved to {current_status}",
        email_body=(
            "Claim {claim_id} transitioned from {previous_status} to {current_status}. "
            "Reason: {reason}."
        ),
        sms_body="Claim {claim_id} now in {current_status}.",
    ),
    "claim_approved": NotificationTemplate(
        key="claim_approved",
        subject="Claim approved: {claim_id}",
        email_body=(
            "Claim {claim_id} has been approved. The payout workflow will begin next."
        ),
        sms_body="Claim {claim_id} approved.",
    ),
    "claim_rejected": NotificationTemplate(
        key="claim_rejected",
        subject="Claim update: {claim_id} rejected",
        email_body="Claim {claim_id} has been rejected. Reason: {reason}.",
        sms_body="Claim {claim_id} rejected.",
    ),
    "payout_initiated": NotificationTemplate(
        key="payout_initiated",
        subject="Payout initiated for claim {claim_id}",
        email_body=(
            "The payout workflow for claim {claim_id} is now underway. "
            "Current status: {current_status}."
        ),
        sms_body="Payout started for claim {claim_id}.",
    ),
    "adjuster_assigned": NotificationTemplate(
        key="adjuster_assigned",
        subject="Adjuster assigned to claim {claim_id}",
        email_body=(
            "Adjuster {adjuster_name} has been assigned to claim {claim_id}."
        ),
        sms_body="Adjuster assigned to claim {claim_id}.",
    ),
}


def dispatch_claim_notification(
    session: Session,
    claim: Claim,
    event_name: str,
    *,
    reason: str | None = None,
    previous_status: str | None = None,
    adjuster_name: str | None = None,
    override_message: str | None = None,
) -> dict:
    template = resolve_template(event_name, claim.status)
    context = {
        "claim_id": str(claim.id),
        "policy_number": claim.policy_number,
        "current_status": claim.status.value,
        "previous_status": previous_status or "N/A",
        "reason": reason or "No additional context provided",
        "adjuster_name": adjuster_name or "Assigned adjuster",
    }

    deliveries: list[dict] = []
    for payload in build_delivery_payloads(template, context, override_message):
        deliveries.append(
            {
                "channel": payload.channel,
                "recipient": payload.recipient,
                "subject": payload.subject,
                "content": payload.content,
                "delivered": True,
            }
        )

    record_audit_event(
        session,
        entity_type="notification",
        entity_id=str(claim.id),
        claim_id=claim.id,
        action="CLAIM_NOTIFICATION_DISPATCHED",
        details={
            "event_name": event_name,
            "channels": [delivery["channel"] for delivery in deliveries],
            "delivery_count": len(deliveries),
        },
    )
    session.commit()

    return {
        "claim_id": str(claim.id),
        "event_name": event_name,
        "channels": [delivery["channel"] for delivery in deliveries],
        "delivered": True,
        "deliveries": deliveries,
    }


def resolve_template(event_name: str, current_status: ClaimStatus) -> NotificationTemplate:
    if event_name in TEMPLATES:
        return TEMPLATES[event_name]

    status_map = {
        ClaimStatus.APPROVED: TEMPLATES["claim_approved"],
        ClaimStatus.REJECTED: TEMPLATES["claim_rejected"],
        ClaimStatus.PAYOUT: TEMPLATES["payout_initiated"],
    }
    return status_map.get(current_status, TEMPLATES["workflow_transition"])


def build_delivery_payloads(
    template: NotificationTemplate,
    context: dict[str, str],
    override_message: str | None,
) -> list[NotificationPayload]:
    email_content = override_message or template.email_body.format(**context)
    sms_content = override_message or template.sms_body.format(**context)

    return [
        NotificationPayload(
            channel="email",
            recipient=f"claimant+{context['claim_id']}@example.com",
            subject=template.subject.format(**context),
            content=email_content,
        ),
        NotificationPayload(
            channel="sms",
            recipient="+910000000000",
            subject=None,
            content=sms_content,
        ),
    ]
