# -*- coding: utf-8 -*-
"""
backend/tests/test_attribution.py

Unit and integration tests for the Attribution Engine (Stage 4).

Tests coverage:
1. First-Touch Attribution (single, multi, non-converted, empty)
2. Last-Touch Attribution (single, multi, non-converted, empty)
3. Linear Attribution (1-ch, 2-ch, repeated channels, exact conservation)
4. Time-Decay Attribution (weight ordering, half-life sensitivity, conservation)
5. Position-Based Attribution (1 touch, 2 touches, 3 touches, 4+ touches, repeated, conservation)
6. Markov Attribution (two-channel, repeated channel, single-channel, non-conversions, zero-effect, conservation)
7. Engine Integration & Validation (dispatch, invalid model errors, parameter pass-through)
"""

import math
from datetime import datetime, timezone, timedelta
import pytest

from backend.app.services.journey_service import (
    CustomerJourney,
    JourneyEvent,
    build_journey,
)
from backend.app.services.attribution import (
    AttributionCredit,
    AttributionResult,
    calculate_first_touch_attribution,
    calculate_last_touch_attribution,
    calculate_linear_attribution,
    calculate_time_decay_attribution,
    calculate_position_based_attribution,
    calculate_markov_attribution,
    calculate_attribution,
)


# =============================================================================
# Test Fixtures & Helpers
# =============================================================================

def make_journey(
    customer_id: str = "cust-001",
    channels: list[str] | None = None,
    converted: bool = True,
    revenue: float = 120.0,
    days_ago: float = 5.0,
) -> CustomerJourney:
    """Helper to build a CustomerJourney with mock events and touchpoints."""
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    conv_time = now if converted else None

    if channels is None:
        channels = ["Google Search", "Facebook"]

    events: list[JourneyEvent] = []
    first_seen = now - timedelta(days=days_ago)

    for i, ch in enumerate(channels):
        ts = first_seen + timedelta(hours=i * 6)
        events.append(
            JourneyEvent(
                timestamp=ts,
                session_id=f"sess-{i}",
                channel=ch,
                event_type="click",
            )
        )

    conv_row = {"timestamp": conv_time, "revenue": revenue, "order_id": "ord-1"} if converted else None

    return build_journey(
        customer_id=customer_id,
        first_seen=first_seen,
        events=events,
        conversion_row=conv_row,
    )


# =============================================================================
# 1. First-Touch Attribution Tests
# =============================================================================

class TestFirstTouchAttribution:
    def test_single_channel(self):
        journey = make_journey(channels=["Google Search"], revenue=100.0)
        res = calculate_first_touch_attribution(journey)

        assert res.model == "first_touch"
        assert res.customer_id == journey.customer_id
        assert res.conversion_revenue == 100.0
        assert res.total_credit == 1.0
        assert len(res.credits) == 1
        assert res.credits[0].channel == "Google Search"
        assert res.credits[0].credit == 1.0
        assert res.credits[0].attributed_revenue == 100.0

    def test_multiple_channels(self):
        journey = make_journey(channels=["Email", "Facebook", "Google Search"], revenue=250.0)
        res = calculate_first_touch_attribution(journey)

        assert res.total_credit == 1.0
        assert len(res.credits) == 1
        assert res.credits[0].channel == "Email"
        assert res.credits[0].attributed_revenue == 250.0
        assert res.get_channel_credit("Email") == 1.0
        assert res.get_channel_credit("Facebook") == 0.0

    def test_non_converted_journey(self):
        journey = make_journey(channels=["Email", "Facebook"], converted=False)
        res = calculate_first_touch_attribution(journey)

        assert res.conversion_revenue == 0.0
        assert res.total_credit == 0.0
        assert res.credits == []

    def test_empty_channels(self):
        journey = make_journey(channels=[], converted=True, revenue=50.0)
        res = calculate_first_touch_attribution(journey)

        assert res.total_credit == 0.0
        assert res.credits == []


# =============================================================================
# 2. Last-Touch Attribution Tests
# =============================================================================

class TestLastTouchAttribution:
    def test_single_channel(self):
        journey = make_journey(channels=["Facebook"], revenue=150.0)
        res = calculate_last_touch_attribution(journey)

        assert res.model == "last_touch"
        assert res.total_credit == 1.0
        assert len(res.credits) == 1
        assert res.credits[0].channel == "Facebook"
        assert res.credits[0].attributed_revenue == 150.0

    def test_multiple_channels(self):
        journey = make_journey(channels=["Email", "Facebook", "Google Search"], revenue=300.0)
        res = calculate_last_touch_attribution(journey)

        assert res.total_credit == 1.0
        assert len(res.credits) == 1
        assert res.credits[0].channel == "Google Search"
        assert res.credits[0].attributed_revenue == 300.0
        assert res.get_channel_credit("Google Search") == 1.0
        assert res.get_channel_credit("Email") == 0.0

    def test_non_converted_journey(self):
        journey = make_journey(channels=["Google Search"], converted=False)
        res = calculate_last_touch_attribution(journey)

        assert res.conversion_revenue == 0.0
        assert res.total_credit == 0.0
        assert res.credits == []

    def test_empty_channels(self):
        journey = make_journey(channels=[], converted=True, revenue=75.0)
        res = calculate_last_touch_attribution(journey)

        assert res.total_credit == 0.0
        assert res.credits == []


# =============================================================================
# 3. Linear Attribution Tests
# =============================================================================

class TestLinearAttribution:
    def test_single_channel(self):
        journey = make_journey(channels=["Google Search"], revenue=80.0)
        res = calculate_linear_attribution(journey)

        assert res.model == "linear"
        assert len(res.credits) == 1
        assert res.credits[0].credit == 1.0
        assert res.credits[0].attributed_revenue == 80.0
        assert res.total_credit == 1.0

    def test_two_channels(self):
        journey = make_journey(channels=["Google Search", "Facebook"], revenue=100.0)
        res = calculate_linear_attribution(journey)

        assert len(res.credits) == 2
        assert res.get_channel_credit("Google Search") == pytest.approx(0.5)
        assert res.get_channel_credit("Facebook") == pytest.approx(0.5)
        assert res.get_channel_revenue("Google Search") == pytest.approx(50.0)
        assert res.get_channel_revenue("Facebook") == pytest.approx(50.0)
        assert res.total_credit == pytest.approx(1.0)

    def test_repeated_channel_handling(self):
        # Instagram -> Google -> Instagram -> Email (4 touches total)
        # Instagram appears twice = 2/4 = 50%
        # Google = 1/4 = 25%
        # Email = 1/4 = 25%
        now = datetime(2026, 1, 15, tzinfo=timezone.utc)
        events = [
            JourneyEvent(timestamp=now + timedelta(hours=1), session_id="s1", channel="Instagram", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(hours=2), session_id="s2", channel="Google Search", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(hours=3), session_id="s3", channel="Instagram", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(hours=4), session_id="s4", channel="Email", event_type="click"),
        ]
        journey = build_journey(
            customer_id="cust-repeat",
            first_seen=now,
            events=events,
            conversion_row={"timestamp": now + timedelta(hours=5), "revenue": 200.0, "order_id": "ord-r"},
        )
        assert journey.channels == ["Instagram", "Google Search", "Instagram", "Email"]

        res = calculate_linear_attribution(journey)

        assert len(res.credits) == 3  # Aggregated into 3 distinct channels
        assert res.get_channel_credit("Instagram") == pytest.approx(0.50)
        assert res.get_channel_credit("Google Search") == pytest.approx(0.25)
        assert res.get_channel_credit("Email") == pytest.approx(0.25)

        assert res.get_channel_revenue("Instagram") == pytest.approx(100.0)
        assert res.get_channel_revenue("Google Search") == pytest.approx(50.0)
        assert res.get_channel_revenue("Email") == pytest.approx(50.0)

    def test_exact_revenue_conservation(self):
        journey = make_journey(channels=["A", "B", "C", "D", "E"], revenue=149.99)
        res = calculate_linear_attribution(journey)

        total_rev = sum(c.attributed_revenue for c in res.credits)
        assert math.isclose(total_rev, res.conversion_revenue, rel_tol=1e-5)
        assert math.isclose(res.total_credit, 1.0, rel_tol=1e-5)

    def test_non_converted_journey(self):
        journey = make_journey(channels=["A", "B"], converted=False)
        res = calculate_linear_attribution(journey)
        assert res.credits == []
        assert res.total_credit == 0.0


# =============================================================================
# 4. Time-Decay Attribution Tests
# =============================================================================

class TestTimeDecayAttribution:
    def test_recent_touch_gets_more_weight(self):
        # Channel A is 7 days before conversion, Channel B is 0 days before conversion (conversion day)
        now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            JourneyEvent(timestamp=now - timedelta(days=7), session_id="s1", channel="OlderChannel", event_type="click"),
            JourneyEvent(timestamp=now, session_id="s2", channel="RecentChannel", event_type="click"),
        ]
        journey = build_journey(
            customer_id="cust-td",
            first_seen=now - timedelta(days=7),
            events=events,
            conversion_row={"timestamp": now, "revenue": 150.0, "order_id": "ord-td"},
        )

        res = calculate_time_decay_attribution(journey, half_life=7.0)

        # Older touch at day 7: weight = 0.5 ** (7/7) = 0.5
        # Recent touch at day 0: weight = 0.5 ** 0 = 1.0
        # Ratio Recent / Older = 2.0
        credit_older = res.get_channel_credit("OlderChannel")
        credit_recent = res.get_channel_credit("RecentChannel")

        assert credit_recent > credit_older
        assert credit_recent == pytest.approx(credit_older * 2.0, rel=1e-3)
        assert res.total_credit == pytest.approx(1.0)

    def test_half_life_changes_result(self):
        now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        events = [
            JourneyEvent(timestamp=now - timedelta(days=7), session_id="s1", channel="Touch1", event_type="click"),
            JourneyEvent(timestamp=now, session_id="s2", channel="Touch2", event_type="click"),
        ]
        journey = build_journey(
            customer_id="cust-hl",
            first_seen=now - timedelta(days=7),
            events=events,
            conversion_row={"timestamp": now, "revenue": 100.0, "order_id": "ord-hl"},
        )

        res_hl7 = calculate_time_decay_attribution(journey, half_life=7.0)
        res_hl1 = calculate_time_decay_attribution(journey, half_life=1.0)

        # With 1-day half-life, Touch1 decays much faster (weight = 0.5**7 = ~0.0078)
        # So Touch2 gets vastly more share
        assert res_hl1.get_channel_credit("Touch2") > res_hl7.get_channel_credit("Touch2")

    def test_exact_revenue_conservation(self):
        journey = make_journey(channels=["Ch1", "Ch2", "Ch3"], revenue=234.56)
        res = calculate_time_decay_attribution(journey, half_life=5.0)

        total_rev = sum(c.attributed_revenue for c in res.credits)
        assert math.isclose(total_rev, res.conversion_revenue, rel_tol=1e-5)
        assert math.isclose(res.total_credit, 1.0, rel_tol=1e-5)

    def test_non_converted_journey(self):
        journey = make_journey(channels=["Ch1", "Ch2"], converted=False)
        res = calculate_time_decay_attribution(journey)
        assert res.credits == []
        assert res.total_credit == 0.0


# =============================================================================
# 5. Position-Based Attribution Tests
# =============================================================================

class TestPositionBasedAttribution:
    def test_one_touch(self):
        journey = make_journey(channels=["Google Search"], revenue=100.0)
        res = calculate_position_based_attribution(journey)

        assert len(res.credits) == 1
        assert res.credits[0].credit == 1.0
        assert res.credits[0].attributed_revenue == 100.0
        assert res.total_credit == 1.0

    def test_two_touches(self):
        journey = make_journey(channels=["Google Search", "Facebook"], revenue=100.0)
        res = calculate_position_based_attribution(journey)

        assert len(res.credits) == 2
        assert res.get_channel_credit("Google Search") == pytest.approx(0.5)
        assert res.get_channel_credit("Facebook") == pytest.approx(0.5)
        assert res.get_channel_revenue("Google Search") == pytest.approx(50.0)
        assert res.get_channel_revenue("Facebook") == pytest.approx(50.0)
        assert res.total_credit == pytest.approx(1.0)

    def test_three_touches(self):
        # 3 touches: First = 40%, Middle = 20%, Last = 40%
        journey = make_journey(channels=["Email", "Google Search", "Facebook"], revenue=200.0)
        res = calculate_position_based_attribution(journey)

        assert res.get_channel_credit("Email") == pytest.approx(0.40)
        assert res.get_channel_credit("Google Search") == pytest.approx(0.20)
        assert res.get_channel_credit("Facebook") == pytest.approx(0.40)

        assert res.get_channel_revenue("Email") == pytest.approx(80.0)
        assert res.get_channel_revenue("Google Search") == pytest.approx(40.0)
        assert res.get_channel_revenue("Facebook") == pytest.approx(80.0)
        assert res.total_credit == pytest.approx(1.0)

    def test_four_plus_touches(self):
        # 4 touches: First = 40%, Middle = 20% / 2 = 10% each, Last = 40%
        journey = make_journey(channels=["A", "B", "C", "D"], revenue=100.0)
        res = calculate_position_based_attribution(journey)

        assert res.get_channel_credit("A") == pytest.approx(0.40)
        assert res.get_channel_credit("B") == pytest.approx(0.10)
        assert res.get_channel_credit("C") == pytest.approx(0.10)
        assert res.get_channel_credit("D") == pytest.approx(0.40)
        assert res.total_credit == pytest.approx(1.0)

    def test_repeated_channel_accumulation(self):
        # Instagram -> Google Search -> Instagram
        # Instagram is first (40%) and last (40%) -> total 80%
        # Google Search is middle (20%) -> total 20%
        now = datetime(2026, 1, 15, tzinfo=timezone.utc)
        events = [
            JourneyEvent(timestamp=now + timedelta(hours=1), session_id="s1", channel="Instagram", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(hours=2), session_id="s2", channel="Google Search", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(hours=3), session_id="s3", channel="Instagram", event_type="click"),
        ]
        journey = build_journey(
            customer_id="cust-pb-rep",
            first_seen=now,
            events=events,
            conversion_row={"timestamp": now + timedelta(hours=4), "revenue": 100.0, "order_id": "ord-pb"},
        )

        res = calculate_position_based_attribution(journey)

        assert len(res.credits) == 2
        assert res.get_channel_credit("Instagram") == pytest.approx(0.80)
        assert res.get_channel_credit("Google Search") == pytest.approx(0.20)
        assert res.get_channel_revenue("Instagram") == pytest.approx(80.0)
        assert res.get_channel_revenue("Google Search") == pytest.approx(20.0)
        assert res.total_credit == pytest.approx(1.0)

    def test_revenue_conservation(self):
        journey = make_journey(channels=["Ch1", "Ch2", "Ch3", "Ch4", "Ch5"], revenue=499.95)
        res = calculate_position_based_attribution(journey)

        total_rev = sum(c.attributed_revenue for c in res.credits)
        assert math.isclose(total_rev, res.conversion_revenue, rel_tol=1e-5)
        assert math.isclose(res.total_credit, 1.0, rel_tol=1e-5)


# =============================================================================
# 6. Markov Attribution Tests
# =============================================================================

class TestMarkovAttribution:
    def test_simple_two_channel_journeys(self):
        # Journey 1: A -> B -> CONVERSION
        # Journey 2: B -> CONVERSION
        # B is on both conversion paths; removing B cuts off 100% of conversions.
        # A is only on one path; removing A cuts off half of conversions.
        j1 = make_journey(customer_id="j1", channels=["ChannelA", "ChannelB"], revenue=100.0)
        j2 = make_journey(customer_id="j2", channels=["ChannelB"], revenue=100.0)

        res = calculate_markov_attribution([j1, j2])

        assert res.model == "markov"
        assert res.conversion_revenue == 200.0
        assert res.total_credit == pytest.approx(1.0)

        credit_a = res.get_channel_credit("ChannelA")
        credit_b = res.get_channel_credit("ChannelB")

        # B should have strictly higher attribution credit than A
        assert credit_b > credit_a
        # Mathematically: Removal effect B = 1.0, A = 0.5 => Shares: B = 2/3 (66.7%), A = 1/3 (33.3%)
        assert credit_b == pytest.approx(2.0 / 3.0, rel=1e-3)
        assert credit_a == pytest.approx(1.0 / 3.0, rel=1e-3)

        assert res.get_channel_revenue("ChannelB") == pytest.approx(200.0 * (2.0 / 3.0), rel=1e-3)
        assert res.get_channel_revenue("ChannelA") == pytest.approx(200.0 * (1.0 / 3.0), rel=1e-3)

    def test_repeated_channel_journeys(self):
        # Journey: Instagram -> Google Search -> Instagram -> CONVERSION
        now = datetime(2026, 1, 15, tzinfo=timezone.utc)
        events = [
            JourneyEvent(timestamp=now + timedelta(hours=1), session_id="s1", channel="Instagram", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(hours=2), session_id="s2", channel="Google Search", event_type="click"),
            JourneyEvent(timestamp=now + timedelta(hours=3), session_id="s3", channel="Instagram", event_type="click"),
        ]
        journey = build_journey(
            customer_id="cust-markov-rep",
            first_seen=now,
            events=events,
            conversion_row={"timestamp": now + timedelta(hours=4), "revenue": 120.0, "order_id": "ord-m"},
        )

        res = calculate_markov_attribution([journey])

        assert res.total_credit == pytest.approx(1.0)
        # Instagram appears twice (both entrance and exit), so its removal effect is higher
        assert res.get_channel_credit("Instagram") > res.get_channel_credit("Google Search")

    def test_one_channel_journeys(self):
        j1 = make_journey(customer_id="j1", channels=["Google Search"], revenue=75.0)
        res = calculate_markov_attribution([j1])

        assert res.total_credit == 1.0
        assert len(res.credits) == 1
        assert res.credits[0].channel == "Google Search"
        assert res.credits[0].credit == 1.0
        assert res.credits[0].attributed_revenue == 75.0

    def test_missing_conversions(self):
        # Cohort has 1 converted journey and 1 non-converted journey
        j_conv = make_journey(customer_id="conv", channels=["Google Search", "Email"], converted=True, revenue=100.0)
        j_drop = make_journey(customer_id="drop", channels=["Google Search"], converted=False, revenue=0.0)

        res = calculate_markov_attribution([j_conv, j_drop])

        assert res.conversion_revenue == 100.0
        assert res.total_credit == pytest.approx(1.0)
        assert len(res.credits) == 2

    def test_no_conversions_in_cohort(self):
        j1 = make_journey(customer_id="drop1", channels=["Google Search"], converted=False)
        j2 = make_journey(customer_id="drop2", channels=["Facebook"], converted=False)

        res = calculate_markov_attribution([j1, j2])

        assert res.conversion_revenue == 0.0
        assert res.total_credit == 0.0
        assert res.credits == []

    def test_empty_input(self):
        res = calculate_markov_attribution([])

        assert res.conversion_revenue == 0.0
        assert res.total_credit == 0.0
        assert res.credits == []

    def test_zero_removal_effect_fallback(self):
        # When removal effects are 0 (e.g. perfectly symmetric or degenerate graph),
        # shares should cleanly fallback to 1 / M equal share
        j1 = make_journey(customer_id="j1", channels=["ChannelA"], revenue=50.0)
        j2 = make_journey(customer_id="j2", channels=["ChannelB"], revenue=50.0)

        res = calculate_markov_attribution([j1, j2])

        assert res.total_credit == pytest.approx(1.0)
        assert res.get_channel_credit("ChannelA") == pytest.approx(0.5)
        assert res.get_channel_credit("ChannelB") == pytest.approx(0.5)

    def test_revenue_conservation(self):
        j1 = make_journey(customer_id="j1", channels=["A", "B"], revenue=123.45)
        j2 = make_journey(customer_id="j2", channels=["B", "C"], revenue=67.89)
        j3 = make_journey(customer_id="j3", channels=["A", "C"], revenue=210.00)

        res = calculate_markov_attribution([j1, j2, j3])

        total_rev = sum(c.attributed_revenue for c in res.credits)
        expected_rev = 123.45 + 67.89 + 210.00
        assert math.isclose(total_rev, expected_rev, rel_tol=1e-5)
        assert math.isclose(res.total_credit, 1.0, rel_tol=1e-5)


# =============================================================================
# 7. Engine Integration Tests
# =============================================================================

class TestAttributionEngine:
    def test_engine_dispatches_all_models(self):
        journey = make_journey(channels=["Email", "Facebook", "Google Search"], revenue=100.0)

        models = ["first_touch", "last_touch", "linear", "time_decay", "position_based", "markov"]
        for m in models:
            res = calculate_attribution(journey, model=m)
            assert res.model == m
            assert res.customer_id == journey.customer_id
            assert res.conversion_revenue == 100.0
            assert res.total_credit == pytest.approx(1.0)
            assert len(res.credits) >= 1

    def test_invalid_model_name_raises(self):
        journey = make_journey()
        with pytest.raises(ValueError, match="Unknown attribution model: 'invalid_model'"):
            calculate_attribution(journey, model="invalid_model")

    def test_invalid_model_type_raises(self):
        journey = make_journey()
        with pytest.raises(ValueError, match="Invalid model parameter type"):
            calculate_attribution(journey, model=123)

    def test_kwargs_passthrough(self):
        journey = make_journey(channels=["Email", "Google Search"], revenue=100.0)
        res = calculate_attribution(journey, model="time_decay", half_life=3.0)
        assert res.model == "time_decay"
        assert res.total_credit == pytest.approx(1.0)

    def test_batch_attribution_on_multiple_journeys(self):
        journeys = [
            make_journey(customer_id=f"cust-{i}", channels=["Google Search", "Email"], revenue=100.0 + i * 10)
            for i in range(5)
        ]
        results = [calculate_attribution(j, model="linear") for j in journeys]

        assert len(results) == 5
        for idx, r in enumerate(results):
            assert r.customer_id == f"cust-{idx}"
            assert r.conversion_revenue == 100.0 + idx * 10
            assert r.total_credit == pytest.approx(1.0)
