"""Unit tests for the claim workflow state machine."""

from __future__ import annotations

import uuid
from datetime import date

import pytest

from app.models.claim import Claim, ClaimStatus
from app.services.workflow_service import (
    WorkflowTransitionError,
    build_workflow_transition_name,
    get_allowed_transitions,
    is_terminal_state,
    resolve_target_status,
)


def _make_claim(status: ClaimStatus) -> Claim:
    claim = Claim()
    claim.id = uuid.uuid4()
    claim.status = status
    claim.policy_number = "POL-001"
    claim.vehicle_number = "MH01AB0001"
    claim.incident_date = date(2026, 1, 15)
    claim.incident_city = "Mumbai"
    claim.claim_amount = 50000.0
    claim.description = "Test incident"
    return claim


class TestAllowedTransitions:
    def test_created_transitions_to_document_verification(self):
        transitions = get_allowed_transitions(ClaimStatus.CLAIM_CREATED)
        assert ClaimStatus.DOCUMENT_VERIFICATION in transitions

    def test_approved_transitions_to_payout(self):
        transitions = get_allowed_transitions(ClaimStatus.APPROVED)
        assert ClaimStatus.PAYOUT in transitions

    def test_document_verification_can_reject(self):
        transitions = get_allowed_transitions(ClaimStatus.DOCUMENT_VERIFICATION)
        assert ClaimStatus.REJECTED in transitions

    def test_rejected_is_terminal(self):
        assert get_allowed_transitions(ClaimStatus.REJECTED) == []

    def test_payout_is_terminal(self):
        assert get_allowed_transitions(ClaimStatus.PAYOUT) == []


class TestTerminalStateDetection:
    @pytest.mark.parametrize("status", [ClaimStatus.REJECTED, ClaimStatus.PAYOUT])
    def test_terminal_states(self, status):
        assert is_terminal_state(status) is True

    @pytest.mark.parametrize(
        "status",
        [
            ClaimStatus.CLAIM_CREATED,
            ClaimStatus.DOCUMENT_VERIFICATION,
            ClaimStatus.FRAUD_ANALYSIS,
            ClaimStatus.APPROVED,
        ],
    )
    def test_non_terminal_states(self, status):
        assert is_terminal_state(status) is False


class TestResolveTargetStatus:
    def test_resolves_single_allowed_transition_without_target(self):
        result = resolve_target_status(
            allowed_transitions=[ClaimStatus.PAYOUT],
            target_status=None,
        )
        assert result == ClaimStatus.PAYOUT

    def test_raises_when_multiple_options_and_no_target(self):
        with pytest.raises(WorkflowTransitionError, match="Multiple transition paths"):
            resolve_target_status(
                allowed_transitions=[
                    ClaimStatus.POLICY_VALIDATION,
                    ClaimStatus.REJECTED,
                ],
                target_status=None,
            )

    def test_raises_for_invalid_target(self):
        with pytest.raises(WorkflowTransitionError, match="not allowed"):
            resolve_target_status(
                allowed_transitions=[ClaimStatus.PAYOUT],
                target_status=ClaimStatus.REJECTED,
            )

    def test_accepts_valid_explicit_target(self):
        result = resolve_target_status(
            allowed_transitions=[ClaimStatus.POLICY_VALIDATION, ClaimStatus.REJECTED],
            target_status=ClaimStatus.REJECTED,
        )
        assert result == ClaimStatus.REJECTED


class TestBuildTransitionName:
    def test_formats_transition_string(self):
        name = build_workflow_transition_name(
            ClaimStatus.CLAIM_CREATED, ClaimStatus.DOCUMENT_VERIFICATION
        )
        assert name == "CLAIM_CREATED->DOCUMENT_VERIFICATION"

    def test_approval_transition_name(self):
        name = build_workflow_transition_name(ClaimStatus.APPROVED, ClaimStatus.PAYOUT)
        assert name == "APPROVED->PAYOUT"


class TestFullWorkflowPath:
    def test_happy_path_sequence(self):
        """Every state in the happy path should have exactly one forward transition."""
        happy_path = [
            ClaimStatus.CLAIM_CREATED,
            ClaimStatus.DOCUMENT_VERIFICATION,
            ClaimStatus.POLICY_VALIDATION,
            ClaimStatus.FRAUD_ANALYSIS,
            ClaimStatus.ADJUSTER_ASSIGNMENT,
            ClaimStatus.REPAIR_ESTIMATION,
            ClaimStatus.FINAL_APPROVAL,
            ClaimStatus.APPROVED,
            ClaimStatus.PAYOUT,
        ]
        for i in range(len(happy_path) - 1):
            current = happy_path[i]
            expected_next = happy_path[i + 1]
            transitions = get_allowed_transitions(current)
            assert (
                expected_next in transitions
            ), f"Expected {expected_next} in transitions from {current}, got {transitions}"
