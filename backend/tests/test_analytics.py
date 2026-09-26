# -*- coding: utf-8 -*-
"""
backend/tests/test_analytics.py

Comprehensive unit and integration tests for Stage 5:
- Overview Analytics (KPI calculations, conversion rate, AOV, zero-division safety)
- Channel Performance (metrics aggregation, unique customer counting, revenue, sorting)
- Attribution Analytics (all 6 models, invalid model, revenue conservation, repeated channels)
- Attribution Comparison (all 6 models present, deterministic output, revenue conservation)
- Journey Patterns (path grouping, non-consecutive duplicates, deterministic sorting, limit validation)
- Analytics API Endpoints (FastAPI routing, HTTP 200/400/500, error message sanitization)
"""

import math
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from backend.app.services.journey_service import (
    CustomerJourney,
    JourneyEvent,
    build_journey,
)
from backend.app.services.analytics import (
    OverviewAnalytics,
    ChannelAnalytics,
    AttributionAnalytics,
    AttributionComparison,
    JourneyPattern,
    calculate_overview_analytics,
    calculate_channel_analytics,
    calculate_attribution_analytics,
    calculate_attribution_comparison,
    calculate_journey_patterns,
)

# Override database dependency with mock so no PostgreSQL connection is attempted in unit tests
app.dependency_overrides[get_db] = lambda: MagicMock()
client = TestClient(app)


# =============================================================================
# Test Fixtures & Helpers
# =============================================================================

def make_sample_journey(
    customer_id: str,
    channels: list[str],
    converted: bool = False,
    revenue: float = 0.0,
    base_time: datetime | None = None,
) -> CustomerJourney:
    """Construct a CustomerJourney with mock events and touchpoints."""
    if base_time is None:
        base_time = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)

    events: list[JourneyEvent] = []
    for idx, ch in enumerate(channels):
        ts = base_time + timedelta(hours=idx * 2)
        events.append(
            JourneyEvent(
                timestamp=ts,
                session_id=f"sess-{customer_id}-{idx}",
                channel=ch,
                event_type="click",
            )
        )

    conv_row = None
    if converted:
        conv_time = base_time + timedelta(hours=len(channels) * 2 + 1)
        conv_row = {
            "timestamp": conv_time,
            "revenue": revenue,
            "order_id": f"ord-{customer_id}",
        }

    return build_journey(
        customer_id=customer_id,
        first_seen=base_time,
        events=events,
        conversion_row=conv_row,
    )


@pytest.fixture
def sample_cohort() -> list[CustomerJourney]:
    """A realistic cohort of 4 customer journeys for unit testing."""
    t0 = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    return [
        # Customer 1: Instagram -> Google Search -> Converted $100
        make_sample_journey("c1", ["Instagram", "Google Search"], converted=True, revenue=100.0, base_time=t0),
        # Customer 2: Google Search -> Converted $200
        make_sample_journey("c2", ["Google Search"], converted=True, revenue=200.0, base_time=t0),
        # Customer 3: Instagram -> Google Search -> Instagram -> Email -> Converted $150
        make_sample_journey("c3", ["Instagram", "Google Search", "Instagram", "Email"], converted=True, revenue=150.0, base_time=t0),
        # Customer 4: Facebook -> Instagram -> Dropped out (Not converted)
        make_sample_journey("c4", ["Facebook", "Instagram"], converted=False, revenue=0.0, base_time=t0),
    ]


# =============================================================================
# 1. Overview Analytics Tests
# =============================================================================

class TestOverviewAnalytics:
    def test_overview_metrics_calculation(self, sample_cohort):
        overview = calculate_overview_analytics(sample_cohort)

        assert overview.customers == 4
        assert overview.conversions == 3
        assert overview.conversion_rate == pytest.approx(3 / 4, rel=1e-3)
        assert overview.total_revenue == pytest.approx(450.0)
        assert overview.average_order_value == pytest.approx(150.0)  # 450 / 3
        assert overview.events == sum(j.event_count for j in sample_cohort)
        assert overview.sessions == sum(j.session_count for j in sample_cohort)
        assert overview.average_journey_duration_minutes > 0
        assert overview.average_touchpoints > 0
        assert overview.unique_channels == 4  # Instagram, Google Search, Email, Facebook

    def test_overview_empty_cohort_zero_division(self):
        overview = calculate_overview_analytics([])

        assert overview.customers == 0
        assert overview.events == 0
        assert overview.sessions == 0
        assert overview.conversions == 0
        assert overview.conversion_rate == 0.0
        assert overview.total_revenue == 0.0
        assert overview.average_order_value == 0.0
        assert overview.average_journey_duration_minutes == 0.0
        assert overview.average_touchpoints == 0.0
        assert overview.unique_channels == 0

    def test_overview_zero_conversions(self):
        cohort = [
            make_sample_journey("c1", ["Instagram"], converted=False),
            make_sample_journey("c2", ["Google Search"], converted=False),
        ]
        overview = calculate_overview_analytics(cohort)

        assert overview.customers == 2
        assert overview.conversions == 0
        assert overview.conversion_rate == 0.0
        assert overview.total_revenue == 0.0
        assert overview.average_order_value == 0.0


# =============================================================================
# 2. Channel Performance Tests
# =============================================================================

class TestChannelAnalytics:
    def test_channel_metrics_aggregation(self, sample_cohort):
        channels = calculate_channel_analytics(sample_cohort)
        ch_map = {c.channel: c for c in channels}

        # Google Search was touched by c1, c2, c3 (all 3 converted)
        assert "Google Search" in ch_map
        gs = ch_map["Google Search"]
        assert gs.customers == 3
        assert gs.conversions == 3
        assert gs.conversion_rate == 1.0
        assert gs.revenue == pytest.approx(450.0)  # 100 + 200 + 150
        assert gs.average_revenue == pytest.approx(150.0)

        # Instagram was touched by c1, c3, c4 (c1, c3 converted; c4 did not)
        assert "Instagram" in ch_map
        insta = ch_map["Instagram"]
        assert insta.customers == 3
        assert insta.conversions == 2
        assert insta.conversion_rate == pytest.approx(2 / 3, rel=1e-3)
        assert insta.revenue == pytest.approx(250.0)  # 100 + 150
        assert insta.average_revenue == pytest.approx(125.0)

        # Facebook was touched only by c4 (not converted)
        assert "Facebook" in ch_map
        fb = ch_map["Facebook"]
        assert fb.customers == 1
        assert fb.conversions == 0
        assert fb.conversion_rate == 0.0
        assert fb.revenue == 0.0
        assert fb.average_revenue == 0.0

    def test_channel_unique_customer_counting(self):
        # Customer has 3 Instagram events; should count as 1 customer
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        events = [
            JourneyEvent(timestamp=now, session_id="s1", channel="Instagram", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(minutes=5), session_id="s1", channel="Instagram", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(hours=1), session_id="s2", channel="Instagram", event_type="click"),
        ]
        journey = build_journey("cust-multi", now, events, None)
        channels = calculate_channel_analytics([journey])

        assert len(channels) == 1
        assert channels[0].channel == "Instagram"
        assert channels[0].customers == 1
        assert channels[0].events == 3

    def test_channel_sorting_revenue_descending(self, sample_cohort):
        channels = calculate_channel_analytics(sample_cohort)
        revenues = [c.revenue for c in channels]
        assert revenues == sorted(revenues, reverse=True)


# =============================================================================
# 3. Attribution Analytics Tests
# =============================================================================

class TestAttributionAnalytics:
    def test_all_six_models(self, sample_cohort):
        models = ["first_touch", "last_touch", "linear", "time_decay", "position_based", "markov"]
        for m in models:
            res = calculate_attribution_analytics(sample_cohort, model=m)
            assert res.model == m
            assert res.total_revenue == pytest.approx(450.0)
            assert len(res.channels) > 0
            # Check credit sums to ~1.0
            total_credit = sum(c.credit for c in res.channels)
            assert total_credit == pytest.approx(1.0, rel=1e-3)
            # Check revenue conservation
            total_attr_rev = sum(c.attributed_revenue for c in res.channels)
            assert math.isclose(total_attr_rev, 450.0, rel_tol=1e-4, abs_tol=0.05)

    def test_invalid_model_raises(self, sample_cohort):
        with pytest.raises(ValueError, match="Invalid attribution model"):
            calculate_attribution_analytics(sample_cohort, model="unknown_model")

    def test_repeated_channel_attribution(self):
        # Instagram -> Google -> Instagram -> Email (converted $200)
        j = make_sample_journey(
            "c_rep",
            ["Instagram", "Google Search", "Instagram", "Email"],
            converted=True,
            revenue=200.0,
        )
        res = calculate_attribution_analytics([j], model="linear")
        ch_credits = {c.channel: c.credit for c in res.channels}

        # Instagram appeared 2/4 times = 50%
        assert ch_credits["Instagram"] == pytest.approx(0.50)
        assert ch_credits["Google Search"] == pytest.approx(0.25)
        assert ch_credits["Email"] == pytest.approx(0.25)

    def test_empty_cohort_attribution(self):
        res = calculate_attribution_analytics([], model="linear")
        assert res.total_revenue == 0.0
        assert res.channels == []


# =============================================================================
# 4. Attribution Comparison Tests
# =============================================================================

class TestAttributionComparison:
    def test_all_six_models_present(self, sample_cohort):
        comp = calculate_attribution_comparison(sample_cohort)
        expected_models = {"first_touch", "last_touch", "linear", "time_decay", "position_based", "markov"}
        assert set(comp.models.keys()) == expected_models

    def test_revenue_conservation_every_model(self, sample_cohort):
        comp = calculate_attribution_comparison(sample_cohort)
        assert comp.total_revenue == pytest.approx(450.0)

        for model_name, channels in comp.models.items():
            model_rev = sum(c.attributed_revenue for c in channels)
            assert math.isclose(model_rev, 450.0, rel_tol=1e-4, abs_tol=0.05)


# =============================================================================
# 5. Journey Patterns Tests
# =============================================================================

class TestJourneyPatterns:
    def test_pattern_grouping_and_metrics(self, sample_cohort):
        patterns = calculate_journey_patterns(sample_cohort, limit=20)

        # 4 journeys have 4 distinct paths
        assert len(patterns) == 4

        # Verify Google Search solo path (Customer 2, revenue 200, converted 1/1 = 100%)
        gs_pattern = next(p for p in patterns if p.path == ["Google Search"])
        assert gs_pattern.customers == 1
        assert gs_pattern.conversions == 1
        assert gs_pattern.conversion_rate == 1.0
        assert gs_pattern.revenue == 200.0

    def test_repeated_non_consecutive_channel_preserved(self, sample_cohort):
        patterns = calculate_journey_patterns(sample_cohort, limit=20)
        rep_pattern = next(
            (p for p in patterns if p.path == ["Instagram", "Google Search", "Instagram", "Email"]),
            None,
        )
        assert rep_pattern is not None
        assert rep_pattern.customers == 1
        assert rep_pattern.conversions == 1
        assert rep_pattern.revenue == 150.0

    def test_patterns_sorted_by_revenue_descending(self, sample_cohort):
        patterns = calculate_journey_patterns(sample_cohort, limit=20)
        revs = [p.revenue for p in patterns]
        assert revs == sorted(revs, reverse=True)

    def test_limit_truncation(self, sample_cohort):
        patterns = calculate_journey_patterns(sample_cohort, limit=2)
        assert len(patterns) == 2

    def test_invalid_limit_raises(self, sample_cohort):
        with pytest.raises(ValueError, match="Limit must be an integer between 1 and 1000"):
            calculate_journey_patterns(sample_cohort, limit=0)

        with pytest.raises(ValueError, match="Limit must be an integer between 1 and 1000"):
            calculate_journey_patterns(sample_cohort, limit=-5)

        with pytest.raises(ValueError, match="Limit must be an integer between 1 and 1000"):
            calculate_journey_patterns(sample_cohort, limit=1001)


# =============================================================================
# 6. API Endpoint Tests (TestClient)
# =============================================================================

class TestAnalyticsAPIEndpoints:
    @patch("app.main.get_overview_analytics")
    def test_get_overview_200(self, mock_overview):
        mock_overview.return_value = OverviewAnalytics(
            customers=500,
            events=3002,
            sessions=1200,
            conversions=28,
            conversion_rate=0.056,
            total_revenue=2393.66,
            average_order_value=85.49,
            average_journey_duration_minutes=420.5,
            average_touchpoints=3.2,
            unique_channels=10,
        )
        r = client.get("/api/analytics/overview")
        assert r.status_code == 200
        body = r.json()
        assert body["customers"] == 500
        assert body["conversions"] == 28
        assert body["total_revenue"] == 2393.66

    @patch("app.main.get_channel_analytics")
    def test_get_channels_200(self, mock_channels):
        mock_channels.return_value = [
            ChannelAnalytics(
                channel="Google Search",
                customers=350,
                events=1200,
                sessions=500,
                conversions=20,
                conversion_rate=0.0571,
                revenue=1800.0,
                average_revenue=90.0,
            )
        ]
        r = client.get("/api/analytics/channels")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["channel"] == "Google Search"
        assert body[0]["revenue"] == 1800.0

    @patch("app.main.get_attribution_analytics")
    def test_get_attribution_linear_200(self, mock_attr):
        mock_attr.return_value = AttributionAnalytics(
            model="linear",
            total_revenue=2393.66,
            channels=[],
        )
        r = client.get("/api/analytics/attribution?model=linear")
        assert r.status_code == 200
        body = r.json()
        assert body["model"] == "linear"
        assert body["total_revenue"] == 2393.66

    def test_get_attribution_invalid_model_400(self):
        r = client.get("/api/analytics/attribution?model=fake_model")
        assert r.status_code == 400
        assert "Invalid attribution model" in r.json()["detail"]

    @patch("app.main.get_attribution_comparison")
    def test_get_attribution_compare_200(self, mock_compare):
        mock_compare.return_value = AttributionComparison(
            models={
                "first_touch": [],
                "last_touch": [],
                "linear": [],
                "time_decay": [],
                "position_based": [],
                "markov": [],
            },
            total_revenue=2393.66,
        )
        r = client.get("/api/analytics/attribution/compare")
        assert r.status_code == 200
        body = r.json()
        assert "models" in body
        assert "linear" in body["models"]
        assert "markov" in body["models"]

    @patch("app.main.get_journey_patterns")
    def test_get_journeys_200(self, mock_journeys):
        mock_journeys.return_value = [
            JourneyPattern(
                path=["Instagram", "Google Search"],
                customers=15,
                conversions=5,
                conversion_rate=0.3333,
                revenue=500.0,
                average_journey_duration_minutes=120.0,
                average_touchpoints=2.0,
            )
        ]
        r = client.get("/api/analytics/journeys?limit=10")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["path"] == ["Instagram", "Google Search"]

    def test_get_journeys_invalid_limit_400(self):
        r = client.get("/api/analytics/journeys?limit=0")
        assert r.status_code == 400

        r_neg = client.get("/api/analytics/journeys?limit=-10")
        assert r_neg.status_code == 400

    @patch("app.main.get_overview_analytics")
    def test_db_error_sanitization_500(self, mock_overview):
        mock_overview.side_effect = RuntimeError("FATAL: relation 'customers' does not exist")
        r = client.get("/api/analytics/overview")
        assert r.status_code == 500
        # Ensure raw DB relation/error message is sanitized
        assert "FATAL: relation" not in r.json()["detail"]
        assert "Internal error" in r.json()["detail"]
