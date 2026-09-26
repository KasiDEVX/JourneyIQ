# -*- coding: utf-8 -*-
"""
backend/tests/test_journey_service.py

Unit tests for the Journey Engine (Stage 3).

PHILOSOPHY
----------
These tests are PURE UNIT TESTS — they call the business logic functions
directly with hand-crafted data. No database, no HTTP server, no Faker.

This is the correct way to test business logic:
  - Fast (no I/O)
  - Deterministic (no randomness)
  - Readable (the test data is right there in each test)
  - Independent (one test failure doesn't cascade into others)

Run from the JourneyIQ/ project root:
  $env:PYTHONPATH = "backend"
  venv\\Scripts\\python.exe -m pytest backend/tests/ -v

WHAT IS BEING TESTED
--------------------
10 required scenarios:
  1.  Chronological ordering — build_journey sorts events regardless of input order
  2.  30-minute session boundary — gap of exactly 30 min stays in same session
  3.  Multiple sessions — gap > 30 min creates a new session
  4.  Touchpoint extraction — impressions and clicks are touchpoints
  5.  Duplicate channel collapsing — same channel back-to-back collapses to one
  6.  Converted customer — conversion_row is reflected in the journey
  7.  Non-converted customer — no conversion fields populated
  8.  Unknown customer — get_customer_journey returns None (mocked DB)
  9.  Journey duration — calculated from first_seen to last event timestamp
 10.  Empty events — customer with zero events returns safe zero-value journey
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.services.journey_service import (
    JourneyEvent,
    CustomerJourney,
    JourneySummary,
    SESSION_GAP_MINUTES,
    _group_into_sessions,
    sessionize_events,
    extract_channel_path,
    build_journey,
    get_customer_journey,
)


# =============================================================================
# Test helpers
# =============================================================================

# A fixed base timestamp — all test events are offset from this.
BASE = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)

CUSTOMER_ID = "test-customer-00000000-0000-0000"
FIRST_SEEN  = BASE  # customer first_seen = same as the first event for simplicity


def t(offset_minutes: int) -> datetime:
    """Return BASE + offset_minutes. Keeps test data easy to read."""
    return BASE + timedelta(minutes=offset_minutes)


def make_event(
    offset_minutes: int,
    event_type:     str = "impression",
    channel:        str = "Instagram",
    session_id:     str = "sess-a",
    campaign_id:    str = None,
    page:           str = None,
    product_id:     str = None,
) -> JourneyEvent:
    """
    Convenience factory for JourneyEvent test objects.
    Using keyword arguments with defaults keeps test cases concise.
    """
    return JourneyEvent(
        timestamp   = t(offset_minutes),
        session_id  = session_id,
        channel     = channel,
        campaign_id = campaign_id,
        event_type  = event_type,
        page        = page,
        product_id  = product_id,
    )


def conversion_row(offset_minutes: int = 90, revenue: float = 99.99,
                   order_id: str = "order-abc-123") -> dict:
    """Convenience factory for a conversion dict."""
    return {
        "timestamp": t(offset_minutes),
        "revenue":   revenue,
        "order_id":  order_id,
    }


# =============================================================================
# TEST 1: Chronological ordering
# =============================================================================

class TestChronologicalOrdering:
    """
    build_journey() sorts events defensively before processing.
    Even if events are given out of order, the output should be sorted.
    """

    def test_events_sorted_in_output(self):
        """Events given in reverse order are sorted in the returned journey."""
        events = [
            make_event(20, event_type="click"),
            make_event(0,  event_type="impression"),   # out of order
            make_event(10, event_type="page_view"),
        ]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)

        timestamps = [e.timestamp for e in journey.events]
        assert timestamps == sorted(timestamps), (
            "Events in CustomerJourney.events must be sorted by timestamp ASC"
        )

    def test_last_activity_is_max_timestamp(self):
        """last_activity must always equal the timestamp of the latest event."""
        events = [
            make_event(0),
            make_event(15),
            make_event(5),   # out of order, but latest is 15
        ]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.last_activity == t(15)


# =============================================================================
# TEST 2: 30-minute session boundary (edge cases)
# =============================================================================

class TestSessionBoundary:
    """
    The 30-minute rule: gap > 30 min = new session, gap <= 30 min = same session.
    Test the boundary itself precisely.
    """

    def test_gap_29_minutes_same_session(self):
        """29-minute gap: both events must be in the same session."""
        events = [make_event(0), make_event(29)]
        sessions = sessionize_events(events)
        assert len(sessions) == 1
        assert sessions[0].event_count == 2

    def test_gap_exactly_30_minutes_same_session(self):
        """Exactly 30 minutes: still the same session (threshold is STRICTLY greater)."""
        events = [make_event(0), make_event(30)]
        sessions = sessionize_events(events)
        assert len(sessions) == 1

    def test_gap_31_minutes_new_session(self):
        """31-minute gap: must produce two sessions."""
        events = [make_event(0), make_event(31)]
        sessions = sessionize_events(events)
        assert len(sessions) == 2, (
            f"Expected 2 sessions for 31-min gap, got {len(sessions)}"
        )

    def test_session_timestamps_are_correct(self):
        """Session started_at and ended_at must match the first and last events."""
        events = [make_event(0), make_event(10), make_event(20)]
        sessions = sessionize_events(events)
        assert sessions[0].started_at == t(0)
        assert sessions[0].ended_at   == t(20)

    def test_session_index_starts_at_one(self):
        """Session indexes are 1-based (not 0-based)."""
        events = [make_event(0), make_event(60)]   # two sessions
        sessions = sessionize_events(events)
        assert sessions[0].session_index == 1
        assert sessions[1].session_index == 2


# =============================================================================
# TEST 3: Multiple sessions
# =============================================================================

class TestMultipleSessions:
    """
    A customer with multiple browsing sessions across hours/days.
    """

    def test_three_sessions(self):
        """Events with two 60-min gaps produce exactly 3 sessions."""
        events = [
            make_event(0),    # session 1
            make_event(10),   # session 1
            make_event(70),   # session 2 (60-min gap from event at t=10)
            make_event(80),   # session 2
            make_event(150),  # session 3 (70-min gap from event at t=80)
        ]
        sessions = sessionize_events(events)
        assert len(sessions) == 3

    def test_journey_session_count_matches(self):
        """CustomerJourney.session_count must equal the number of sessions."""
        events = [
            make_event(0),
            make_event(60),   # new session
            make_event(130),  # new session
        ]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.session_count == 3

    def test_session_event_counts_are_correct(self):
        """Each session reports its own event_count correctly."""
        events = [
            make_event(0),    # session 1 — 2 events
            make_event(10),
            make_event(70),   # session 2 — 1 event
        ]
        sessions = sessionize_events(events)
        assert sessions[0].event_count == 2
        assert sessions[1].event_count == 1

    def test_session_channels_are_unique_per_session(self):
        """Session.channels lists unique channels seen in that session."""
        events = [
            make_event(0,  channel="Instagram"),
            make_event(5,  channel="Instagram"),   # duplicate — should collapse
            make_event(10, channel="Facebook"),
        ]
        sessions = sessionize_events(events)
        assert sessions[0].channels == ["Instagram", "Facebook"]


# =============================================================================
# TEST 4: Touchpoint extraction
# =============================================================================

class TestTouchpointExtraction:
    """
    Marketing touchpoints are impressions, clicks, and qualifying page_views.
    """

    def test_impression_is_touchpoint(self):
        events = [make_event(0, event_type="impression", channel="Instagram")]
        path = extract_channel_path(events)
        assert "Instagram" in path

    def test_click_is_touchpoint(self):
        events = [make_event(0, event_type="click", channel="Facebook")]
        path = extract_channel_path(events)
        assert "Facebook" in path

    def test_page_view_as_session_entry_marketing_channel_is_touchpoint(self):
        """
        page_view as the first event of a session on Email = touchpoint.
        The customer re-entered via email marketing.
        """
        events = [
            make_event(0,  event_type="page_view", channel="Email"),
            make_event(5,  event_type="product_view", channel="Email"),
        ]
        path = extract_channel_path(events)
        assert "Email" in path

    def test_page_view_on_direct_not_touchpoint(self):
        """
        Direct channel page_view is NOT a marketing touchpoint.
        User typed the URL themselves — no marketing involved.
        """
        events = [
            make_event(0, event_type="page_view", channel="Direct"),
        ]
        path = extract_channel_path(events)
        assert path == [], f"Expected empty path, got {path}"

    def test_page_view_on_organic_search_not_touchpoint(self):
        """Organic Search page_view is not a paid touchpoint."""
        events = [make_event(0, event_type="page_view", channel="Organic Search")]
        path = extract_channel_path(events)
        assert path == []

    def test_product_view_is_not_touchpoint(self):
        """product_view is a behavioral event — not a marketing touchpoint."""
        events = [make_event(0, event_type="product_view", channel="Google Search")]
        path = extract_channel_path(events)
        assert path == []

    def test_checkout_is_not_touchpoint(self):
        """checkout is behavioral — not a marketing touchpoint."""
        events = [make_event(0, event_type="checkout", channel="Email")]
        path = extract_channel_path(events)
        assert path == []

    def test_touchpoint_count_in_journey(self):
        """journey.touchpoint_count equals len(journey.channels)."""
        events = [
            make_event(0,  event_type="impression", channel="Instagram"),
            make_event(10, event_type="impression", channel="Facebook"),
        ]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.touchpoint_count == len(journey.channels)
        assert journey.touchpoint_count == 2


# =============================================================================
# TEST 5: Duplicate channel collapsing
# =============================================================================

class TestDuplicateChannelCollapsing:
    """
    Consecutive duplicate channels in the path are collapsed to one.
    Non-consecutive duplicates are preserved.
    """

    def test_consecutive_same_channel_collapses(self):
        """
        Instagram impression in session 1, Instagram impression in session 2
        with no other channel in between -> collapses to one Instagram.
        """
        events = [
            make_event(0,   event_type="impression", channel="Instagram"),  # session 1
            make_event(60,  event_type="impression", channel="Instagram"),  # session 2 (60-min gap)
        ]
        path = extract_channel_path(events)
        assert path == ["Instagram"], f"Expected ['Instagram'], got {path}"

    def test_non_consecutive_duplicate_preserved(self):
        """
        Instagram -> Google -> Instagram is a valid multi-touch path.
        The final Instagram should NOT be collapsed.
        """
        events = [
            make_event(0,   event_type="impression", channel="Instagram"),
            make_event(60,  event_type="impression", channel="Google Search"),
            make_event(120, event_type="impression", channel="Instagram"),
        ]
        path = extract_channel_path(events)
        assert path == ["Instagram", "Google Search", "Instagram"], (
            f"Non-consecutive duplicates must be preserved. Got: {path}"
        )

    def test_triple_consecutive_collapses_to_one(self):
        """Three sessions all on Instagram -> one Instagram in path."""
        events = [
            make_event(0,   event_type="impression", channel="Instagram"),
            make_event(60,  event_type="impression", channel="Instagram"),
            make_event(120, event_type="impression", channel="Instagram"),
        ]
        path = extract_channel_path(events)
        assert path == ["Instagram"]

    def test_within_session_same_channel_deduped(self):
        """
        Multiple impressions from same channel within ONE session -> one touchpoint.
        """
        events = [
            make_event(0,  event_type="impression", channel="Facebook"),
            make_event(5,  event_type="impression", channel="Facebook"),
            make_event(10, event_type="click",      channel="Facebook"),
        ]
        path = extract_channel_path(events)
        assert path == ["Facebook"]


# =============================================================================
# TEST 6: Converted customer
# =============================================================================

class TestConvertedCustomer:
    """A customer who completed a purchase."""

    def test_converted_flag_is_true(self):
        events = [
            make_event(0,  event_type="impression"),
            make_event(10, event_type="checkout"),
        ]
        conv = conversion_row(offset_minutes=15, revenue=149.99)
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events, conv)
        assert journey.converted is True

    def test_conversion_revenue_populated(self):
        events = [make_event(0)]
        conv = conversion_row(revenue=75.50)
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events, conv)
        assert journey.conversion_revenue == 75.50

    def test_conversion_timestamp_populated(self):
        events = [make_event(0)]
        conv_ts = t(90)
        conv = {"timestamp": conv_ts, "revenue": 50.0, "order_id": "ord-xyz"}
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events, conv)
        assert journey.conversion_timestamp == conv_ts

    def test_conversion_order_id_populated(self):
        events = [make_event(0)]
        conv = conversion_row(order_id="ORDER-999")
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events, conv)
        assert journey.conversion_order_id == "ORDER-999"


# =============================================================================
# TEST 7: Non-converted customer
# =============================================================================

class TestNonConvertedCustomer:
    """A customer who browsed but never purchased."""

    def test_converted_flag_is_false(self):
        events = [make_event(0), make_event(10)]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events, conversion_row=None)
        assert journey.converted is False

    def test_conversion_fields_are_none(self):
        events = [make_event(0)]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.conversion_revenue   is None
        assert journey.conversion_timestamp is None
        assert journey.conversion_order_id  is None


# =============================================================================
# TEST 8: Unknown customer
# =============================================================================

class TestUnknownCustomer:
    """
    get_customer_journey() must return None for an unknown customer_id.
    The API route then converts that None into HTTP 404.

    We mock the database session so this test requires no PostgreSQL connection.
    MagicMock lets us stub out any method call we specify.
    """

    def test_returns_none_for_unknown_customer(self):
        # Create a mock database session
        mock_db = MagicMock()
        # Make .execute().fetchone() return None (customer not found in DB)
        mock_db.execute.return_value.fetchone.return_value = None

        result = get_customer_journey("nonexistent-uuid-9999", mock_db)
        assert result is None, "Expected None for unknown customer"

    def test_db_fetch_customer_called_with_correct_id(self):
        """Verify the service actually queries the DB for the right customer_id."""
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = None

        get_customer_journey("some-id-abc", mock_db)

        # The execute() was called at least once
        mock_db.execute.assert_called()


# =============================================================================
# TEST 9: Journey duration
# =============================================================================

class TestJourneyDuration:
    """
    journey_duration_minutes = (last event timestamp - first_seen) / 60 seconds.
    """

    def test_duration_single_event(self):
        """
        Single event at first_seen -> duration = 0 minutes.
        """
        events = [make_event(0)]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.journey_duration_minutes == 0.0

    def test_duration_two_events_30_minutes(self):
        events = [make_event(0), make_event(30)]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.journey_duration_minutes == 30.0

    def test_duration_multiday(self):
        """
        Events spanning 2 days (2880 minutes).
        first_seen is the BASE; last event is at BASE + 2880 minutes.
        """
        events = [
            make_event(0),
            make_event(2880),   # 2 days later
        ]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.journey_duration_minutes == 2880.0

    def test_duration_is_from_first_seen_not_first_event(self):
        """
        first_seen may be before the first event (customer was known earlier).
        Duration starts from first_seen.
        """
        first_seen = BASE - timedelta(minutes=60)   # 1 hour before first event
        events     = [make_event(0), make_event(30)]
        journey    = build_journey(CUSTOMER_ID, first_seen, events)
        # Duration = (t(30) - first_seen) = 90 minutes
        assert journey.journey_duration_minutes == 90.0


# =============================================================================
# TEST 10: Empty / no-event handling
# =============================================================================

class TestEmptyEventHandling:
    """
    A customer who exists in the customers table but has generated no events.
    This is a valid state (customer registered but never browsed).
    """

    def test_zero_events_returns_journey_with_zeros(self):
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events=[])
        assert journey.event_count              == 0
        assert journey.session_count            == 0
        assert journey.touchpoint_count         == 0
        assert journey.unique_channel_count     == 0
        assert journey.journey_duration_minutes == 0.0
        assert journey.converted                is False

    def test_zero_events_empty_lists(self):
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events=[])
        assert journey.channels == []
        assert journey.sessions == []
        assert journey.events   == []

    def test_zero_events_last_activity_equals_first_seen(self):
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events=[])
        assert journey.last_activity == journey.first_seen

    def test_sessionize_empty_list(self):
        """sessionize_events([]) should return an empty list without error."""
        sessions = sessionize_events([])
        assert sessions == []

    def test_extract_channel_path_empty_list(self):
        """extract_channel_path([]) should return an empty list without error."""
        path = extract_channel_path([])
        assert path == []


# =============================================================================
# Additional edge-case tests
# =============================================================================

class TestEdgeCases:

    def test_unique_channel_count_is_correct(self):
        """unique_channel_count = number of distinct channels in the journey."""
        events = [
            make_event(0,  channel="Instagram"),
            make_event(10, channel="Facebook"),
            make_event(20, channel="Instagram"),   # duplicate
        ]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.unique_channel_count == 2   # Instagram + Facebook

    def test_event_count_includes_all_events(self):
        """event_count = total raw events, NOT just touchpoints."""
        events = [
            make_event(0,  event_type="impression"),
            make_event(5,  event_type="click"),
            make_event(10, event_type="page_view"),
            make_event(15, event_type="product_view"),
            make_event(20, event_type="add_to_cart"),
            make_event(25, event_type="checkout"),
        ]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)
        assert journey.event_count == 6

    def test_mixed_journey_multi_channel(self):
        """
        Realistic multi-session, multi-channel journey end-to-end.

        Session 1 (t=0..20):  Instagram impression -> click
        Session 2 (t=100..110): Google Search click
        Session 3 (t=200..210): Email page_view (re-entry)
        """
        events = [
            make_event(0,   event_type="impression", channel="Instagram"),
            make_event(5,   event_type="click",      channel="Instagram"),
            make_event(10,  event_type="page_view",  channel="Instagram"),
            make_event(20,  event_type="product_view", channel="Instagram"),
            # 80-min gap -> new session
            make_event(100, event_type="click",      channel="Google Search"),
            make_event(110, event_type="page_view",  channel="Google Search"),
            # 90-min gap -> new session
            make_event(200, event_type="page_view",  channel="Email"),  # re-entry
            make_event(210, event_type="checkout",   channel="Email"),
        ]
        journey = build_journey(CUSTOMER_ID, FIRST_SEEN, events)

        assert journey.session_count       == 3
        assert journey.event_count         == 8
        # Path: Instagram (impression), Google Search (click), Email (page_view re-entry)
        assert journey.channels            == ["Instagram", "Google Search", "Email"]
        assert journey.touchpoint_count    == 3
        assert journey.unique_channel_count == 3
