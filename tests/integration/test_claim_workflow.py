"""Integration tests: full claim lifecycle via the FastAPI HTTP layer."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("httpx")


@pytest.fixture(scope="module")
def client():
    from unittest.mock import patch

    with (
        patch("app.db.session.init_db"),
        patch("app.services.document_service.ensure_document_storage"),
    ):
        from app.main import app

        return TestClient(app, raise_server_exceptions=True)


class TestHealthEndpoints:
    def test_health_returns_ok(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_contains_service_name(self, client):
        response = client.get("/api/v1/health")
        assert "service" in response.json()

    def test_readiness_endpoint_exists(self, client):
        response = client.get("/api/v1/ready")
        assert response.status_code in (200, 503)


class TestOpenAPISchema:
    def test_openapi_json_accessible(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_docs_endpoint_accessible(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_key_routes_present_in_schema(self, client):
        schema = client.get("/openapi.json").json()
        paths = schema["paths"]
        assert any("/claims" in p for p in paths)
        assert any("/auth" in p for p in paths)
        assert any("/workflow" in p for p in paths)


class TestAuthFlow:
    def test_register_requires_valid_email(self, client):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "full_name": "Test",
                "password": "pass",
                "role": "adjuster",
            },
        )
        assert response.status_code == 422

    def test_login_with_missing_credentials_fails(self, client):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "", "password": ""},
        )
        assert response.status_code in (401, 422)

    def test_protected_endpoint_requires_token(self, client):
        response = client.get("/api/v1/claims")
        assert response.status_code == 401


class TestRateLimitHeaders:
    def test_responses_include_rate_limit_headers(self, client):
        response = client.get("/api/v1/health")
        assert "x-ratelimit-limit" in response.headers
        assert "x-ratelimit-remaining" in response.headers

    def test_correlation_id_header_in_response(self, client):
        response = client.get("/api/v1/health")
        assert "x-correlation-id" in response.headers

    def test_correlation_id_is_echoed_when_sent(self, client):
        correlation_id = "test-correlation-123"
        response = client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": correlation_id},
        )
        assert response.headers.get("x-correlation-id") == correlation_id


class TestClaimValidation:
    def test_create_claim_requires_auth(self, client):
        response = client.post(
            "/api/v1/claims",
            json={
                "policy_number": "POL-001",
                "vehicle_number": "MH01AB0001",
                "incident_date": "2026-01-15",
                "incident_city": "Mumbai",
                "claim_amount": 50000.0,
                "description": "Test",
            },
        )
        assert response.status_code == 401

    def test_settlement_endpoint_exists(self, client):
        response = client.get("/api/v1/claims/some-id/settlements")
        assert response.status_code in (401, 422)

    def test_dlq_endpoint_requires_auth(self, client):
        response = client.get("/api/v1/dlq")
        assert response.status_code == 401

    def test_metrics_endpoint_accessible(self, client):
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
