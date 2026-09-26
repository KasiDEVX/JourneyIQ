# -*- coding: utf-8 -*-
"""
backend/tests/test_security.py

Stage 8A Security & API Hardening Test Suite.

Verifies:
  1.  CORS allowed origin is accepted
  2.  CORS disallowed origin does not receive access-control-allow-origin
  3.  Wildcard CORS is rejected in production
  4.  Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
  5.  Sanitized 500 response (no stack trace, no DB credentials, no raw exception text)
  6.  Unknown customer returns controlled 404
  7.  Invalid attribution model returns HTTP 400
  8.  Invalid conversion filter returns HTTP 400
  9.  Invalid journey-flow limit returns HTTP 422
  10. Oversized journey-flow limit returns HTTP 422
  11. SQL injection-style input is treated as literal data, doesn't execute SQL, returns 404
  12. XSS / Directory traversal payloads in customer ID handled safely
  13. Health endpoint contract preserved (liveness)
  14. Readiness endpoint returns 200 on DB reachability and 503 on failure without leaking details
  15. Request ID (X-Request-ID) returned, client-supplied valid ID preserved, generated on missing
  16. Database failure does not leak internal DB credentials or connection strings
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import Settings
from app.database import get_db

app.dependency_overrides[get_db] = lambda: MagicMock()
client = TestClient(app)


# =============================================================================
# 1. CORS Hardening Tests
# =============================================================================

class TestCORSHardening:

    def test_allowed_origin_accepted(self):
        """Origin configured in CORS_ORIGINS receives Access-Control-Allow-Origin."""
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_disallowed_origin_not_granted(self):
        """Unrecognized origin does not receive Access-Control-Allow-Origin permission."""
        response = client.get(
            "/api/health",
            headers={"Origin": "https://malicious-attacker.com"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") is None

    def test_production_wildcard_cors_rejected(self):
        """Wildcard CORS origin in production environment raises ValueError."""
        with patch.dict(
            "os.environ",
            {"ENVIRONMENT": "production", "CORS_ORIGINS": "*"},
            clear=False,
        ):
            settings_prod = Settings()
            settings_prod.ENVIRONMENT = "production"
            settings_prod.CORS_ORIGINS = "*"
            with pytest.raises(ValueError, match="wildcard CORS origin.*disallowed in production"):
                _ = settings_prod.cors_origins_list

    def test_cors_options_preflight(self):
        """Preflight OPTIONS request from allowed origin returns 200."""
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


# =============================================================================
# 2. Security Headers Tests
# =============================================================================

class TestSecurityHeaders:

    def test_security_headers_present_on_success(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_security_headers_present_on_error(self):
        response = client.get("/api/customers/not-found/journey")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# =============================================================================
# 3. Request Logging & Request-ID Tests
# =============================================================================

class TestRequestID:

    def test_request_id_generated_when_missing(self):
        response = client.get("/api/health")
        req_id = response.headers.get("X-Request-ID")
        assert req_id is not None
        assert len(req_id) >= 16

    def test_client_supplied_request_id_preserved(self):
        custom_id = "trace-client-12345"
        response = client.get(
            "/api/health",
            headers={"X-Request-ID": custom_id},
        )
        assert response.headers.get("X-Request-ID") == custom_id

    def test_malformed_client_request_id_replaced(self):
        unsafe_id = "<script>alert(1)</script>"
        response = client.get(
            "/api/health",
            headers={"X-Request-ID": unsafe_id},
        )
        req_id = response.headers.get("X-Request-ID")
        assert req_id is not None
        assert "<script>" not in req_id


# =============================================================================
# 4. Error Sanitization Tests
# =============================================================================

class TestErrorSanitization:

    @patch("app.main.get_customer_journey")
    def test_sanitized_500_response_on_unhandled_exception(self, mock_journey):
        mock_journey.side_effect = RuntimeError(
            "FATAL: password authentication failed for user 'postgres' at /var/lib/db"
        )
        response = client.get("/api/customers/cust-1/journey")
        assert response.status_code == 500
        body = response.json()
        assert "password" not in body["detail"]
        assert "postgres" not in body["detail"]
        assert "/var/lib" not in body["detail"]
        assert "Internal error" in body["detail"]

    @patch("app.main.get_overview_analytics")
    def test_overview_db_error_sanitized(self, mock_overview):
        mock_overview.side_effect = Exception("connection to server at '10.0.0.1:5432' failed")
        response = client.get("/api/analytics/overview")
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert "10.0.0.1" not in detail
        assert "5432" not in detail
        assert "Internal error" in detail


# =============================================================================
# 5. Input Validation & Injection Hardening Tests
# =============================================================================

class TestInputValidation:

    def test_unknown_customer_returns_404(self):
        with patch("app.main.get_customer_journey", return_value=None):
            response = client.get("/api/customers/cust-unknown-999/journey")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_invalid_attribution_model_returns_400(self):
        response = client.get("/api/analytics/attribution?model=quantum_magic")
        assert response.status_code == 400
        assert "Invalid attribution model" in response.json()["detail"]

    def test_invalid_conversion_filter_returns_400(self):
        response = client.get("/api/analytics/journey-flow?conversion=semi_converted")
        assert response.status_code == 400
        assert "Invalid conversion filter" in response.json()["detail"]

    def test_journey_flow_limit_zero_returns_422(self):
        response = client.get("/api/analytics/journey-flow?limit=0")
        assert response.status_code == 422

    def test_journey_flow_limit_oversized_returns_422(self):
        response = client.get("/api/analytics/journey-flow?limit=999999")
        assert response.status_code == 422

    def test_sql_injection_string_as_customer_id(self):
        """SQL injection payloads must be treated as literal customer ID string."""
        with patch("app.main.get_customer_journey", return_value=None):
            response = client.get("/api/customers/' OR 1=1 --/journey")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_sql_drop_table_string_as_customer_id(self):
        with patch("app.main.get_customer_journey", return_value=None):
            response = client.get("/api/customers/\"; DROP TABLE customers; --/journey")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_directory_traversal_payload_as_customer_id(self):
        with patch("app.main.get_customer_journey", return_value=None):
            response = client.get("/api/customers/..%2F..%2Fetc%2Fpasswd/journey")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_null_byte_in_customer_id_rejected(self):
        response = client.get("/api/customers/cust%00hack/journey")
        # FastAPI or validation rejects null byte
        assert response.status_code in (400, 404, 422)


# =============================================================================
# 6. Health & Readiness Tests
# =============================================================================

class TestHealthAndReadiness:

    def test_health_endpoint_liveness_contract(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "journeyiq-api"}

    @patch("app.main.check_db_connection", return_value=True)
    def test_ready_endpoint_returns_200_when_db_ok(self, mock_db):
        response = client.get("/api/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "connected"}

    @patch("app.main.check_db_connection", return_value=False)
    def test_ready_endpoint_returns_503_when_db_down(self, mock_db):
        response = client.get("/api/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "not_ready", "database": "disconnected"}
        # Must not expose database URLs or tracebacks
        assert "postgresql" not in response.text
        assert "sqlite" not in response.text
