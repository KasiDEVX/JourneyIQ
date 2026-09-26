# -*- coding: utf-8 -*-
"""
backend/tests/test_endpoints.py

FastAPI endpoint tests using TestClient (no real database required).
Uses unittest.mock.patch to substitute the service layer.

Run from project root:
    $env:PYTHONPATH = "backend"
    venv/Scripts/python.exe -m pytest backend/tests/test_endpoints.py -v
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.journey_service import build_journey, JourneyEvent, CustomerProfile

client = TestClient(app)

# ── Shared test journey fixture ───────────────────────────────────────────────

BASE_TS = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)


def _make_test_journey():
    """Build a real CustomerJourney using the service logic (no DB needed)."""
    events = [
        JourneyEvent(
            timestamp=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
            session_id="s1", channel="Instagram", campaign_id="camp-1",
            event_type="impression", page=None, product_id=None,
        ),
        JourneyEvent(
            timestamp=datetime(2026, 6, 1, 10, 10, tzinfo=timezone.utc),
            session_id="s1", channel="Instagram", campaign_id="camp-1",
            event_type="click", page="/home", product_id=None,
        ),
        JourneyEvent(
            timestamp=datetime(2026, 6, 2, 9, 0, tzinfo=timezone.utc),
            session_id="s2", channel="Email", campaign_id="camp-2",
            event_type="page_view", page="/sale", product_id=None,
        ),
    ]
    return build_journey(
        customer_id="cust-endpoint-test",
        first_seen=BASE_TS,
        events=events,
        conversion_row={
            "timestamp": datetime(2026, 6, 2, 9, 30, tzinfo=timezone.utc),
            "revenue": 89.99,
            "order_id": "order-001",
        },
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_returns_200(self):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_response_body(self):
        r = client.get("/api/health")
        assert r.json() == {"status": "ok", "service": "journeyiq-api"}


class TestJourneyEndpoint:

    def test_404_for_unknown_customer(self):
        with patch("app.main.get_customer_journey", return_value=None):
            r = client.get("/api/customers/no-such-id/journey")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()

    def test_200_with_correct_fields(self):
        journey = _make_test_journey()
        with patch("app.main.get_customer_journey", return_value=journey):
            r = client.get("/api/customers/cust-endpoint-test/journey")
        assert r.status_code == 200
        body = r.json()
        assert body["customer_id"]        == "cust-endpoint-test"
        assert body["event_count"]        == 3
        assert body["session_count"]      == 2
        assert body["converted"]          is True
        assert body["conversion_revenue"] == 89.99
        assert body["channels"]           == ["Instagram", "Email"]
        assert body["touchpoint_count"]   == 2

    def test_response_contains_events_list(self):
        journey = _make_test_journey()
        with patch("app.main.get_customer_journey", return_value=journey):
            r = client.get("/api/customers/cust-endpoint-test/journey")
        body = r.json()
        assert "events" in body
        assert len(body["events"]) == 3

    def test_response_contains_sessions_list(self):
        journey = _make_test_journey()
        with patch("app.main.get_customer_journey", return_value=journey):
            r = client.get("/api/customers/cust-endpoint-test/journey")
        body = r.json()
        assert "sessions" in body
        assert len(body["sessions"]) == 2

    def test_events_are_sorted_chronologically(self):
        journey = _make_test_journey()
        with patch("app.main.get_customer_journey", return_value=journey):
            r = client.get("/api/customers/cust-endpoint-test/journey")
        timestamps = [e["timestamp"] for e in r.json()["events"]]
        assert timestamps == sorted(timestamps)


class TestJourneySummaryEndpoint:

    def test_404_for_unknown_customer(self):
        with patch("app.main.get_customer_journey", return_value=None):
            r = client.get("/api/customers/no-such-id/journey/summary")
        assert r.status_code == 404

    def test_200_with_summary_fields(self):
        journey = _make_test_journey()
        with patch("app.main.get_customer_journey", return_value=journey):
            r = client.get("/api/customers/cust-endpoint-test/journey/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["touchpoint_count"]   == 2
        assert body["converted"]          is True
        assert body["conversion_revenue"] == 89.99

    def test_summary_has_no_events_field(self):
        """Summary endpoint must NOT return the events list."""
        journey = _make_test_journey()
        with patch("app.main.get_customer_journey", return_value=journey):
            r = client.get("/api/customers/cust-endpoint-test/journey/summary")
        assert "events" not in r.json()

    def test_summary_has_no_sessions_field(self):
        """Summary endpoint must NOT return the sessions list."""
        journey = _make_test_journey()
        with patch("app.main.get_customer_journey", return_value=journey):
            r = client.get("/api/customers/cust-endpoint-test/journey/summary")
        assert "sessions" not in r.json()

    def test_summary_contains_channels(self):
        journey = _make_test_journey()
        with patch("app.main.get_customer_journey", return_value=journey):
            r = client.get("/api/customers/cust-endpoint-test/journey/summary")
        assert r.json()["channels"] == ["Instagram", "Email"]


class TestListCustomersEndpoint:
    """Tests for GET /api/customers endpoint."""

    def test_list_customers_success(self):
        sample_customers = [
            CustomerProfile(
                customer_id="cust-101",
                first_seen=BASE_TS,
                converted=True,
                conversion_revenue=150.0,
                event_count=5,
            ),
            CustomerProfile(
                customer_id="cust-102",
                first_seen=BASE_TS,
                converted=False,
                conversion_revenue=0.0,
                event_count=2,
            ),
        ]
        with patch("app.main.fetch_customers_list", return_value=sample_customers):
            r = client.get("/api/customers?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        assert data[0]["customer_id"] == "cust-101"
        assert data[0]["converted"] is True
        assert data[0]["conversion_revenue"] == 150.0
        assert data[1]["converted"] is False

    def test_list_customers_with_filters(self):
        with patch("app.main.fetch_customers_list", return_value=[]) as mock_fetch:
            r = client.get("/api/customers?search=test&converted=true&limit=25")
            assert r.status_code == 200
            assert mock_fetch.called

