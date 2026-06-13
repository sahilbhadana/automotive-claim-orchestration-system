"""Integration tests: claim ownership enforced through the HTTP layer.

Uses a dedicated in-memory SQLite database via dependency override so
the full request->auth->authorization->persistence path is exercised
without external services.
"""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

pytest.importorskip("httpx")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    with (
        patch("app.db.session.init_db"),
        patch("app.services.document_service.ensure_document_storage"),
    ):
        from app.main import app

    from app.core.config import settings
    from app.db.session import Base
    from app.db.session import get_db_session

    test_engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine, autoflush=False)

    def override_db_session():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_db_session
    # Expose the session factory so fixtures can provision staff roles,
    # which are no longer self-assignable through registration.
    app.state.test_session_factory = TestSession
    storage_dir = tmp_path_factory.mktemp("doc_storage")
    with patch.object(settings, "document_storage_path", str(storage_dir)):
        yield TestClient(app, raise_server_exceptions=True)
    app.dependency_overrides.pop(get_db_session, None)
    test_engine.dispose()


def _promote(client, user_id: str, role: str) -> None:
    """Grant a staff/admin role directly in the DB. Registration always
    creates customers, so tests provision elevated roles out of band."""
    from app.models.user import UserRole
    from app.services.auth_service import set_user_role

    factory = client.app.state.test_session_factory
    session = factory()
    try:
        set_user_role(session, user_id, UserRole(role))
    finally:
        session.close()


def _register_and_login(client, username: str, role: str = "customer") -> dict:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": username.replace(".", " ").title(),
            "password": "password123",
        },
    )
    assert register.status_code == 201, register.text
    # Public registration is always a customer; the role claim a user
    # sends is ignored. Elevate explicitly when a test needs staff.
    assert register.json()["role"] == "customer"

    login = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "password123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/v1/auth/me", headers=headers)
    user_id = me.json()["id"]
    if role != "customer":
        _promote(client, user_id, role)
    return {"headers": headers, "id": user_id}


@pytest.fixture(scope="module")
def users(client):
    return {
        "owner": _register_and_login(client, "own.customer", "customer"),
        "other": _register_and_login(client, "other.customer", "customer"),
        "admin": _register_and_login(client, "own.admin", "admin"),
    }


@pytest.fixture(scope="module")
def claim(client, users):
    response = client.post(
        "/api/v1/claims",
        headers=users["owner"]["headers"],
        json={
            "policy_number": "POL-OWN-100",
            "vehicle_number": "GJ05ZZ1000",
            "incident_date": "2026-05-20",
            "incident_city": "Surat",
            "claim_amount": 55000.0,
            "description": "Ownership integration test claim",
            "driving_license_number": "GJ0520100012345",
            "license_expiry_date": "2030-01-01",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestClaimVisibility:
    def test_claim_records_its_claimant(self, claim, users):
        assert claim["claimant_id"] == users["owner"]["id"]

    def test_owner_sees_own_claim_in_list(self, client, users, claim):
        response = client.get("/api/v1/claims", headers=users["owner"]["headers"])
        assert claim["id"] in {c["id"] for c in response.json()}

    def test_other_customer_list_excludes_foreign_claim(self, client, users, claim):
        response = client.get("/api/v1/claims", headers=users["other"]["headers"])
        assert claim["id"] not in {c["id"] for c in response.json()}

    def test_other_customer_cannot_fetch_foreign_claim(self, client, users, claim):
        response = client.get(
            f"/api/v1/claims/{claim['id']}", headers=users["other"]["headers"]
        )
        assert response.status_code == 404

    def test_staff_sees_all_claims(self, client, users, claim):
        response = client.get("/api/v1/claims", headers=users["admin"]["headers"])
        assert claim["id"] in {c["id"] for c in response.json()}

    def test_other_customer_cannot_view_activity(self, client, users, claim):
        response = client.get(
            f"/api/v1/claims/{claim['id']}/activity",
            headers=users["other"]["headers"],
        )
        assert response.status_code == 404

    def test_owner_can_view_activity(self, client, users, claim):
        response = client.get(
            f"/api/v1/claims/{claim['id']}/activity",
            headers=users["owner"]["headers"],
        )
        assert response.status_code == 200


class TestDocumentOwnership:
    @staticmethod
    def _upload(client, headers, claim_id):
        return client.post(
            f"/api/v1/claims/{claim_id}/documents",
            headers=headers,
            data={"document_type": "ACCIDENT_PHOTO"},
            files={"file": ("photo.jpg", io.BytesIO(b"jpeg-bytes-here"), "image/jpeg")},
        )

    def test_staff_cannot_upload(self, client, users, claim):
        response = self._upload(client, users["admin"]["headers"], claim["id"])
        assert response.status_code == 403

    def test_non_owner_customer_cannot_upload(self, client, users, claim):
        response = self._upload(client, users["other"]["headers"], claim["id"])
        assert response.status_code == 404

    def test_owner_can_upload_and_download(self, client, users, claim):
        upload = self._upload(client, users["owner"]["headers"], claim["id"])
        assert upload.status_code == 201, upload.text
        document_id = upload.json()["id"]

        download = client.get(
            f"/api/v1/claims/{claim['id']}/documents/{document_id}/download",
            headers=users["owner"]["headers"],
        )
        assert download.status_code == 200
        assert download.content == b"jpeg-bytes-here"

    def test_staff_can_download(self, client, users, claim):
        documents = client.get(
            f"/api/v1/claims/{claim['id']}/documents",
            headers=users["admin"]["headers"],
        ).json()
        assert documents, "expected at least one uploaded document"
        download = client.get(
            f"/api/v1/claims/{claim['id']}/documents/{documents[0]['id']}/download",
            headers=users["admin"]["headers"],
        )
        assert download.status_code == 200

    def test_non_owner_customer_cannot_list_documents(self, client, users, claim):
        response = client.get(
            f"/api/v1/claims/{claim['id']}/documents",
            headers=users["other"]["headers"],
        )
        assert response.status_code == 404


class TestWorkflowAuthority:
    def test_customer_cannot_execute_workflow(self, client, users, claim):
        response = client.post(
            f"/api/v1/claims/{claim['id']}/workflow/execute",
            headers=users["owner"]["headers"],
            json={"target_status": "DOCUMENT_VERIFICATION"},
        )
        assert response.status_code == 403

    def test_customer_can_view_own_workflow_state(self, client, users, claim):
        response = client.get(
            f"/api/v1/claims/{claim['id']}/workflow",
            headers=users["owner"]["headers"],
        )
        assert response.status_code == 200

    def test_staff_can_execute_workflow(self, client, users, claim):
        response = client.post(
            f"/api/v1/claims/{claim['id']}/workflow/execute",
            headers=users["admin"]["headers"],
            json={"target_status": "DOCUMENT_VERIFICATION"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["current_status"] == "DOCUMENT_VERIFICATION"

    def test_customer_cannot_run_fraud_analysis(self, client, users, claim):
        response = client.post(
            f"/api/v1/claims/{claim['id']}/fraud/analyze",
            headers=users["owner"]["headers"],
            json={},
        )
        assert response.status_code == 403

    def test_customer_cannot_patch_claim_status(self, client, users, claim):
        response = client.patch(
            f"/api/v1/claims/{claim['id']}/status",
            headers=users["owner"]["headers"],
            json={"status": "APPROVED"},
        )
        assert response.status_code == 403


class TestPrivilegeEscalation:
    def test_registration_cannot_self_assign_admin(self, client):
        # Even sending role=admin, the created user is a customer.
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "username": "sneaky.admin",
                "email": "sneaky@example.com",
                "full_name": "Sneaky Admin",
                "password": "password123",
                "role": "admin",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "customer"

    def test_customer_cannot_elevate_roles(self, client, users):
        resp = client.patch(
            f"/api/v1/auth/users/{users['other']['id']}/role",
            headers=users["owner"]["headers"],
            json={"role": "admin"},
        )
        assert resp.status_code == 403

    def test_admin_can_elevate_roles(self, client, users):
        target = _register_and_login(client, "promote.me")
        resp = client.patch(
            f"/api/v1/auth/users/{target['id']}/role",
            headers=users["admin"]["headers"],
            json={"role": "adjuster"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "adjuster"


class TestSecondaryEndpointAuthz:
    def test_customer_cannot_list_policies(self, client, users):
        resp = client.get("/api/v1/policies", headers=users["owner"]["headers"])
        assert resp.status_code == 403

    def test_customer_cannot_create_policy(self, client, users):
        resp = client.post(
            "/api/v1/policies",
            headers=users["owner"]["headers"],
            json={
                "policy_number": "POL-XYZ",
                "insured_name": "Test Insured",
                "vehicle_number": "GJ01AA0001",
                "coverage_type": "COMPREHENSIVE",
                "effective_date": "2026-01-01",
                "expiry_date": "2027-01-01",
            },
        )
        assert resp.status_code == 403

    def test_customer_cannot_list_adjusters(self, client, users):
        resp = client.get("/api/v1/adjusters", headers=users["owner"]["headers"])
        assert resp.status_code == 403

    def test_customer_cannot_dispatch_async_workflow(self, client, users, claim):
        # The async path must enforce the same staff-only rule as the sync one.
        resp = client.post(
            f"/api/v1/claims/{claim['id']}/workflow/execute-async",
            headers=users["owner"]["headers"],
            json={"target_status": "DOCUMENT_VERIFICATION"},
        )
        assert resp.status_code == 403

    def test_customer_cannot_read_metrics(self, client, users):
        resp = client.get("/api/v1/metrics/summary", headers=users["owner"]["headers"])
        assert resp.status_code == 403
