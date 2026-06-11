"""Unit tests for claim ownership at the service layer."""

from __future__ import annotations

import uuid
from datetime import date

from app.models.claim import Claim  # noqa: F401 - registers table metadata
from app.models.user import User  # noqa: F401 - registers table metadata
from app.schemas.claim import ClaimCreate
from app.services.claim_service import create_claim
from app.services.claim_service import list_claims


def _payload(vehicle: str = "MH01AB1234") -> ClaimCreate:
    return ClaimCreate(
        policy_number="POL-OWN-001",
        vehicle_number=vehicle,
        incident_date=date(2026, 5, 1),
        incident_city="Mumbai",
        claim_amount=60000.0,
        description="Ownership test claim with enough detail",
    )


class TestClaimOwnership:
    def test_create_claim_stores_claimant_id(self, db_session):
        claimant_id = uuid.uuid4()
        claim = create_claim(db_session, _payload(), claimant_id=claimant_id)
        assert claim.claimant_id == claimant_id

    def test_create_claim_without_claimant_is_unowned(self, db_session):
        claim = create_claim(db_session, _payload("MH01AB0002"))
        assert claim.claimant_id is None

    def test_list_claims_filters_by_claimant(self, db_session):
        owner_a = uuid.uuid4()
        owner_b = uuid.uuid4()
        create_claim(db_session, _payload("KA01AA0001"), claimant_id=owner_a)
        create_claim(db_session, _payload("KA01AA0002"), claimant_id=owner_a)
        create_claim(db_session, _payload("KA01AA0003"), claimant_id=owner_b)

        a_claims = list_claims(db_session, claimant_id=owner_a)
        assert len(a_claims) == 2
        assert all(c.claimant_id == owner_a for c in a_claims)

        b_claims = list_claims(db_session, claimant_id=owner_b)
        assert len(b_claims) == 1

    def test_list_claims_unfiltered_returns_all_owners(self, db_session):
        owner = uuid.uuid4()
        create_claim(db_session, _payload("TN01AA0001"), claimant_id=owner)
        create_claim(db_session, _payload("TN01AA0002"))

        all_claims = list_claims(db_session)
        vehicles = {c.vehicle_number for c in all_claims}
        assert {"TN01AA0001", "TN01AA0002"}.issubset(vehicles)
