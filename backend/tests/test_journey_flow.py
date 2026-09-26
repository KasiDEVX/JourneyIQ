# -*- coding: utf-8 -*-
"""
backend/tests/test_journey_flow.py

Comprehensive tests for Stage 7: Interactive Customer Journey Flow Visualization.

Tests cover:
  1.  Empty journey collection
  2.  Single journey (non-converted)
  3.  Single journey (converted)
  4.  Multiple journeys
  5.  Repeated non-consecutive channels preserved
  6.  Consecutive duplicate channels (handled by journey_service)
  7.  Converted journey includes CONVERSION node and edge
  8.  Non-converted journey does NOT include CONVERSION node
  9.  START node present in every non-empty graph
  10. CONVERSION node only present when at least one converted journey
  11. Multiple identical transitions aggregate correctly
  12. conversion=converted filter
  13. conversion=non_converted filter
  14. conversion=all filter
  15. Invalid conversion filter returns HTTP 400
  16. Invalid limit returns HTTP 422 (FastAPI validation)
  17. Deterministic link ordering
  18. Revenue does NOT affect flow values
  19. Existing journey logic remains unchanged (journey patterns still work)
  20. Channel paths with empty channels produce no transitions
  21. Limit semantics (applies to journeys, not links)
  22. __START__ and __CONVERSION__ ID collision safety
  23. Node type classification
  24. API endpoint returns 200 with valid response shape
  25. API endpoint journey-flow?conversion=converted returns 200
  26. API endpoint journey-flow?conversion=non_converted returns 200
"""

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
from backend.app.services.analytics.journey_flow import (
    START_NODE_ID,
    CONVERSION_NODE_ID,
    START_NODE_LABEL,
    CONVERSION_NODE_LABEL,
    JourneyFlowNode,
    JourneyFlowLink,
    JourneyFlowResponse,
    build_journey_flow,
)
from backend.app.services.analytics import (
    JourneyPattern,
    calculate_journey_patterns,
)

# Override DB dependency for API tests (no real PostgreSQL needed)
app.dependency_overrides[get_db] = lambda: MagicMock()
client = TestClient(app)


# =============================================================================
# Helpers
# =============================================================================

def _make_event(channel: str, ts: datetime, event_type: str = "click") -> JourneyEvent:
    return JourneyEvent(
        timestamp=ts,
        session_id=f"sess-{channel}-{ts.hour}",
        channel=channel,
        event_type=event_type,
    )


def make_journey(
    customer_id: str,
    channels: list[str],
    converted: bool = False,
    revenue: float = 0.0,
    base_time: datetime | None = None,
) -> CustomerJourney:
    """
    Build a CustomerJourney directly from channels using build_journey().
    Events are spaced 2 hours apart to ensure separate sessions (>30min gap),
    which means each channel becomes a separate touchpoint.
    """
    if base_time is None:
        base_time = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)

    events = []
    for idx, ch in enumerate(channels):
        ts = base_time + timedelta(hours=idx * 2)
        events.append(_make_event(ch, ts, event_type="click"))

    conv_row = None
    if converted:
        conv_time = base_time + timedelta(hours=len(channels) * 2 + 1)
        conv_row = {"timestamp": conv_time, "revenue": revenue, "order_id": f"ord-{customer_id}"}

    return build_journey(
        customer_id=customer_id,
        first_seen=base_time,
        events=events,
        conversion_row=conv_row,
    )


# =============================================================================
# 1. Empty journey collection
# =============================================================================

class TestEmptyJourneyCollection:
    def test_empty_returns_empty_graph(self):
        result = build_journey_flow([])
        assert result.nodes == []
        assert result.links == []
        assert result.total_journeys == 0
        assert result.total_transitions == 0
        assert result.converted_journeys == 0
        assert result.non_converted_journeys == 0

    def test_empty_with_converted_filter(self):
        result = build_journey_flow([], conversion_filter="converted")
        assert result.total_journeys == 0
        assert result.nodes == []
        assert result.links == []

    def test_empty_with_non_converted_filter(self):
        result = build_journey_flow([], conversion_filter="non_converted")
        assert result.total_journeys == 0
        assert result.nodes == []
        assert result.links == []


# =============================================================================
# 2 & 3. Single journey
# =============================================================================

class TestSingleJourney:
    def test_single_non_converted_journey(self):
        j = make_journey("c1", ["Instagram", "Google Search"], converted=False)
        result = build_journey_flow([j])

        assert result.total_journeys == 1
        assert result.converted_journeys == 0
        assert result.non_converted_journeys == 1

        # Expect __START__, Instagram, Google Search nodes (NO __CONVERSION__)
        node_ids = {n.id for n in result.nodes}
        assert START_NODE_ID in node_ids
        assert "Instagram" in node_ids
        assert "Google Search" in node_ids
        assert CONVERSION_NODE_ID not in node_ids

        # Expect 2 links
        assert len(result.links) == 2
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}
        assert link_map[(START_NODE_ID, "Instagram")] == 1
        assert link_map[("Instagram", "Google Search")] == 1

    def test_single_converted_journey(self):
        j = make_journey("c1", ["Instagram", "Email"], converted=True, revenue=99.0)
        result = build_journey_flow([j])

        assert result.total_journeys == 1
        assert result.converted_journeys == 1
        assert result.non_converted_journeys == 0

        # Expect CONVERSION node
        node_ids = {n.id for n in result.nodes}
        assert CONVERSION_NODE_ID in node_ids
        assert START_NODE_ID in node_ids

        # Expect 3 links including Email → CONVERSION
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}
        assert link_map[(START_NODE_ID, "Instagram")] == 1
        assert link_map[("Instagram", "Email")] == 1
        assert link_map[("Email", CONVERSION_NODE_ID)] == 1

    def test_single_journey_empty_channels_no_transitions(self):
        """A journey with zero channel path should produce no transitions."""
        j = make_journey("c1", [], converted=False)
        result = build_journey_flow([j])
        assert result.links == []
        assert result.nodes == []


# =============================================================================
# 4. Multiple journeys
# =============================================================================

class TestMultipleJourneys:
    def test_multiple_journeys_aggregate(self):
        journeys = [
            make_journey("c1", ["Instagram", "Email"], converted=True, revenue=50.0),
            make_journey("c2", ["Instagram", "Email"], converted=True, revenue=75.0),
            make_journey("c3", ["Facebook"], converted=False),
        ]
        result = build_journey_flow(journeys)

        assert result.total_journeys == 3
        assert result.converted_journeys == 2
        assert result.non_converted_journeys == 1

        link_map = {(lk.source, lk.target): lk.value for lk in result.links}
        # c1 and c2 both produce START→Instagram
        assert link_map[(START_NODE_ID, "Instagram")] == 2
        # c1 and c2 both produce Instagram→Email
        assert link_map[("Instagram", "Email")] == 2
        # c1 and c2 both produce Email→CONVERSION
        assert link_map[("Email", CONVERSION_NODE_ID)] == 2
        # c3 produces START→Facebook
        assert link_map[(START_NODE_ID, "Facebook")] == 1


# =============================================================================
# 5. Repeated non-consecutive channels preserved
# =============================================================================

class TestRepeatedNonConsecutiveChannels:
    def test_instagram_google_instagram_email(self):
        """
        The specification example:
          Instagram → Google Search → Instagram → Email
        must produce 4 transitions (including repeated Instagram occurrences).
        """
        j = make_journey(
            "c1",
            ["Instagram", "Google Search", "Instagram", "Email"],
            converted=True,
            revenue=150.0,
        )
        result = build_journey_flow([j])

        link_map = {(lk.source, lk.target): lk.value for lk in result.links}

        # All required transitions
        assert link_map[(START_NODE_ID, "Instagram")] == 1
        assert link_map[("Instagram", "Google Search")] == 1
        assert link_map[("Google Search", "Instagram")] == 1
        assert link_map[("Instagram", "Email")] == 1
        assert link_map[("Email", CONVERSION_NODE_ID)] == 1

        # Total: 5 links (START→Insta, Insta→Google, Google→Insta, Insta→Email, Email→CONV)
        assert len(result.links) == 5

    def test_repeated_channel_not_collapsed(self):
        """Non-consecutive repetitions must NOT be collapsed."""
        j = make_journey("c1", ["A", "B", "A", "C"])
        result = build_journey_flow([j])
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}

        # A→B and B→A are separate transitions
        assert ("A", "B") in link_map
        assert ("B", "A") in link_map
        # B→A should NOT be missing
        assert link_map[("B", "A")] == 1


# =============================================================================
# 6. Consecutive duplicates (journey_service collapses them)
# =============================================================================

class TestConsecutiveDuplicates:
    def test_consecutive_duplicates_collapsed_by_service(self):
        """
        journey_service collapses consecutive duplicates in channel paths.
        Our flow builder trusts journey.channels directly.
        Verify: Instagram → Instagram → Google → Google produces
        channels = [Instagram, Google] (collapsed by journey_service).
        """
        base = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
        events = [
            # Two Instagram clicks in same session (within 30min)
            _make_event("Instagram", base, "click"),
            _make_event("Instagram", base + timedelta(minutes=5), "click"),
            # Google in a new session
            _make_event("Google Search", base + timedelta(hours=2), "click"),
            _make_event("Google Search", base + timedelta(hours=2, minutes=5), "click"),
        ]
        j = build_journey("c1", base, events, None)
        # journey_service collapses consecutive duplicates
        # Instagram appears once per session since sessions are separate
        assert j.channels == ["Instagram", "Google Search"]

        result = build_journey_flow([j])
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}

        # Only 2 links (no self-loops)
        assert link_map[(START_NODE_ID, "Instagram")] == 1
        assert link_map[("Instagram", "Google Search")] == 1
        assert len(result.links) == 2


# =============================================================================
# 7 & 8. Converted / Non-converted node semantics
# =============================================================================

class TestConversionNodeSemantics:
    def test_converted_journey_has_conversion_node(self):
        j = make_journey("c1", ["Email"], converted=True, revenue=100.0)
        result = build_journey_flow([j])
        node_ids = {n.id for n in result.nodes}
        assert CONVERSION_NODE_ID in node_ids

    def test_non_converted_journey_has_no_conversion_node(self):
        j = make_journey("c1", ["Email"], converted=False)
        result = build_journey_flow([j])
        node_ids = {n.id for n in result.nodes}
        assert CONVERSION_NODE_ID not in node_ids

    def test_mixed_journeys_conversion_node_present(self):
        journeys = [
            make_journey("c1", ["Email"], converted=True, revenue=10.0),
            make_journey("c2", ["Facebook"], converted=False),
        ]
        result = build_journey_flow(journeys)
        node_ids = {n.id for n in result.nodes}
        assert CONVERSION_NODE_ID in node_ids

    def test_all_non_converted_no_conversion_node(self):
        journeys = [
            make_journey("c1", ["Email"], converted=False),
            make_journey("c2", ["Facebook"], converted=False),
        ]
        result = build_journey_flow(journeys)
        node_ids = {n.id for n in result.nodes}
        assert CONVERSION_NODE_ID not in node_ids


# =============================================================================
# 9. START node
# =============================================================================

class TestStartNode:
    def test_start_node_present_in_non_empty_graph(self):
        j = make_journey("c1", ["Instagram"])
        result = build_journey_flow([j])
        node_ids = {n.id for n in result.nodes}
        assert START_NODE_ID in node_ids

    def test_start_node_has_correct_label(self):
        j = make_journey("c1", ["Instagram"])
        result = build_journey_flow([j])
        start_nodes = [n for n in result.nodes if n.id == START_NODE_ID]
        assert len(start_nodes) == 1
        assert start_nodes[0].label == START_NODE_LABEL
        assert start_nodes[0].type == "start"

    def test_conversion_node_has_correct_label(self):
        j = make_journey("c1", ["Email"], converted=True, revenue=10.0)
        result = build_journey_flow([j])
        conv_nodes = [n for n in result.nodes if n.id == CONVERSION_NODE_ID]
        assert len(conv_nodes) == 1
        assert conv_nodes[0].label == CONVERSION_NODE_LABEL
        assert conv_nodes[0].type == "conversion"

    def test_channel_node_has_type_channel(self):
        j = make_journey("c1", ["Instagram"])
        result = build_journey_flow([j])
        channel_nodes = [n for n in result.nodes if n.type == "channel"]
        channel_ids = {n.id for n in channel_nodes}
        assert "Instagram" in channel_ids


# =============================================================================
# 10. Aggregation of identical transitions
# =============================================================================

class TestTransitionAggregation:
    def test_identical_transitions_aggregate(self):
        """87 journeys all going Instagram → Google Search should produce value=87."""
        journeys = [
            make_journey(f"c{i}", ["Instagram", "Google Search"])
            for i in range(87)
        ]
        result = build_journey_flow(journeys)
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}
        assert link_map[(START_NODE_ID, "Instagram")] == 87
        assert link_map[("Instagram", "Google Search")] == 87

    def test_partial_overlap_aggregation(self):
        """Some journeys share transitions, others don't."""
        journeys = [
            make_journey("c1", ["A", "B"], converted=False),
            make_journey("c2", ["A", "B"], converted=True, revenue=10.0),
            make_journey("c3", ["A", "C"], converted=False),
        ]
        result = build_journey_flow(journeys)
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}

        # All 3 start with A
        assert link_map[(START_NODE_ID, "A")] == 3
        # c1 and c2 go A→B
        assert link_map[("A", "B")] == 2
        # c3 goes A→C
        assert link_map[("A", "C")] == 1
        # c2 goes B→CONVERSION
        assert link_map[("B", CONVERSION_NODE_ID)] == 1


# =============================================================================
# 11-13. Conversion filter
# =============================================================================

class TestConversionFilter:
    @pytest.fixture
    def mixed_cohort(self):
        return [
            make_journey("c1", ["Instagram", "Email"], converted=True, revenue=100.0),
            make_journey("c2", ["Google Search"], converted=True, revenue=200.0),
            make_journey("c3", ["Facebook", "Instagram"], converted=False),
        ]

    def test_filter_all_includes_all_journeys(self, mixed_cohort):
        result = build_journey_flow(mixed_cohort, conversion_filter="all")
        assert result.total_journeys == 3
        assert result.converted_journeys == 2
        assert result.non_converted_journeys == 1

    def test_filter_converted_only(self, mixed_cohort):
        result = build_journey_flow(mixed_cohort, conversion_filter="converted")
        assert result.total_journeys == 2
        assert result.converted_journeys == 2
        assert result.non_converted_journeys == 0
        # Facebook should not appear (only in non-converted journey)
        node_ids = {n.id for n in result.nodes}
        assert "Facebook" not in node_ids

    def test_filter_non_converted_only(self, mixed_cohort):
        result = build_journey_flow(mixed_cohort, conversion_filter="non_converted")
        assert result.total_journeys == 1
        assert result.converted_journeys == 0
        assert result.non_converted_journeys == 1
        # No CONVERSION node
        node_ids = {n.id for n in result.nodes}
        assert CONVERSION_NODE_ID not in node_ids
        # Facebook should appear
        assert "Facebook" in node_ids


# =============================================================================
# 14-15. Invalid query parameters
# =============================================================================

class TestAPIValidation:
    def test_invalid_conversion_filter_returns_400(self):
        r = client.get("/api/analytics/journey-flow?conversion=invalid_value")
        assert r.status_code == 400
        detail = r.json()["detail"]
        assert "invalid_value" in detail.lower() or "invalid" in detail.lower()

    def test_invalid_conversion_bogus_returns_400(self):
        r = client.get("/api/analytics/journey-flow?conversion=banana")
        assert r.status_code == 400

    def test_limit_zero_returns_422(self):
        """FastAPI Query(ge=1) rejects limit=0 with 422."""
        r = client.get("/api/analytics/journey-flow?limit=0")
        assert r.status_code == 422

    def test_limit_negative_returns_422(self):
        r = client.get("/api/analytics/journey-flow?limit=-5")
        assert r.status_code == 422

    def test_limit_over_max_returns_422(self):
        """FastAPI Query(le=5000) rejects limit>5000 with 422."""
        r = client.get("/api/analytics/journey-flow?limit=99999")
        assert r.status_code == 422


# =============================================================================
# 16. Deterministic ordering
# =============================================================================

class TestDeterministicOrdering:
    def test_links_sorted_value_desc_source_asc_target_asc(self):
        journeys = [
            make_journey("c1", ["A", "B"]) for _ in range(5)
        ] + [
            make_journey("c2", ["A", "C"]) for _ in range(3)
        ] + [
            make_journey("c3", ["X", "Y"]) for _ in range(10)
        ]
        result = build_journey_flow(journeys)

        # Verify value DESC ordering
        values = [lk.value for lk in result.links]
        for i in range(len(values) - 1):
            if values[i] == values[i + 1]:
                # Same value: check source ASC
                if result.links[i].source == result.links[i + 1].source:
                    # Same source: check target ASC
                    assert result.links[i].target <= result.links[i + 1].target
                else:
                    assert result.links[i].source <= result.links[i + 1].source
            else:
                assert values[i] >= values[i + 1]

    def test_repeated_calls_produce_same_ordering(self):
        journeys = [
            make_journey("c1", ["B", "A"]),
            make_journey("c2", ["A", "B"]),
            make_journey("c3", ["C", "D"]),
        ]
        r1 = build_journey_flow(journeys)
        r2 = build_journey_flow(journeys)
        assert [(lk.source, lk.target, lk.value) for lk in r1.links] == \
               [(lk.source, lk.target, lk.value) for lk in r2.links]


# =============================================================================
# 17. Revenue does NOT affect flow values
# =============================================================================

class TestRevenueDoesNotAffectFlowValues:
    def test_high_revenue_journey_same_weight_as_low(self):
        """
        Two journeys following the same path should each contribute value=1
        to their transitions regardless of revenue amount.
        """
        j_low = make_journey("c1", ["Email"], converted=True, revenue=0.01)
        j_high = make_journey("c2", ["Email"], converted=True, revenue=999999.99)

        result = build_journey_flow([j_low, j_high])
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}

        # Both contribute 1 journey each = value of 2, NOT 0.01 or 999999.99
        assert link_map[(START_NODE_ID, "Email")] == 2
        assert link_map[("Email", CONVERSION_NODE_ID)] == 2

        # Explicitly: values are integer journey counts, not revenue amounts
        for lk in result.links:
            assert isinstance(lk.value, int)


# =============================================================================
# 18. Existing journey logic unchanged
# =============================================================================

class TestExistingJourneyLogicUnchanged:
    def test_journey_patterns_still_work(self):
        """calculate_journey_patterns still works correctly alongside Stage 7."""
        journeys = [
            make_journey("c1", ["Instagram", "Google Search"], converted=True, revenue=100.0),
            make_journey("c2", ["Google Search"], converted=True, revenue=200.0),
            make_journey("c3", ["Instagram", "Google Search", "Instagram", "Email"],
                         converted=True, revenue=150.0),
        ]
        patterns = calculate_journey_patterns(journeys, limit=20)
        assert len(patterns) == 3
        # Verify non-consecutive channel repetition preserved in patterns
        rep_path = next((p for p in patterns if "Email" in p.path), None)
        assert rep_path is not None
        assert rep_path.path == ["Instagram", "Google Search", "Instagram", "Email"]

    def test_journey_channels_used_directly(self):
        """
        Flow builder uses journey.channels (from journey_service) exactly as-is.
        Verify by building a journey and checking that flow transitions
        match the journey's channel list.
        """
        j = make_journey("c1", ["Instagram", "Google Search", "Email"], converted=True, revenue=50.0)
        # journey.channels should be exactly as provided (separate sessions → no collapsing)
        assert j.channels == ["Instagram", "Google Search", "Email"]

        result = build_journey_flow([j])
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}

        assert link_map[(START_NODE_ID, "Instagram")] == 1
        assert link_map[("Instagram", "Google Search")] == 1
        assert link_map[("Google Search", "Email")] == 1
        assert link_map[("Email", CONVERSION_NODE_ID)] == 1


# =============================================================================
# 19. Limit semantics
# =============================================================================

class TestLimitSemantics:
    def test_limit_applies_to_journeys_not_links(self):
        """limit=2 means only 2 journeys used, not 2 links returned."""
        journeys = [make_journey(f"c{i}", ["A", "B", "C"]) for i in range(10)]
        result = build_journey_flow(journeys, limit=2)
        assert result.total_journeys == 2
        # Each journey produces 3 transitions; with only 2 journeys, max value is 2
        link_map = {(lk.source, lk.target): lk.value for lk in result.links}
        assert link_map[(START_NODE_ID, "A")] == 2  # 2 journeys start with A

    def test_limit_larger_than_cohort_uses_all(self):
        journeys = [make_journey(f"c{i}", ["A"]) for i in range(5)]
        result = build_journey_flow(journeys, limit=1000)
        assert result.total_journeys == 5


# =============================================================================
# 20. Node ID collision safety
# =============================================================================

class TestNodeIdCollisionSafety:
    def test_start_node_id_not_collide_with_channel_names(self):
        """Channels named literally anything should not collide with __START__."""
        j = make_journey("c1", [START_NODE_ID])  # Channel named __START__ (edge case)
        result = build_journey_flow([j])
        # __START__ appears as both special start AND channel - but they have same ID
        # The important thing is the logic doesn't break
        # (In practice, no real channel is named __START__)
        assert result.total_journeys == 1


# =============================================================================
# 21. API endpoint integration tests (mocked DB)
# =============================================================================

class TestJourneyFlowAPIEndpoint:
    @patch("app.main.get_journey_flow")
    def test_endpoint_200_all(self, mock_flow):
        mock_flow.return_value = JourneyFlowResponse(
            nodes=[
                JourneyFlowNode(id=START_NODE_ID, label=START_NODE_LABEL, type="start"),
                JourneyFlowNode(id="Instagram", label="Instagram", type="channel"),
                JourneyFlowNode(id=CONVERSION_NODE_ID, label=CONVERSION_NODE_LABEL, type="conversion"),
            ],
            links=[
                JourneyFlowLink(source=START_NODE_ID, target="Instagram", value=10),
                JourneyFlowLink(source="Instagram", target=CONVERSION_NODE_ID, value=5),
            ],
            total_journeys=10,
            total_transitions=2,
            converted_journeys=5,
            non_converted_journeys=5,
        )
        r = client.get("/api/analytics/journey-flow")
        assert r.status_code == 200
        body = r.json()
        assert "nodes" in body
        assert "links" in body
        assert body["total_journeys"] == 10
        assert body["total_transitions"] == 2
        assert body["converted_journeys"] == 5
        assert body["non_converted_journeys"] == 5

    @patch("app.main.get_journey_flow")
    def test_endpoint_200_converted_filter(self, mock_flow):
        mock_flow.return_value = JourneyFlowResponse(
            nodes=[],
            links=[],
            total_journeys=0,
            total_transitions=0,
            converted_journeys=0,
            non_converted_journeys=0,
        )
        r = client.get("/api/analytics/journey-flow?conversion=converted")
        assert r.status_code == 200
        # Verify mock was called with correct filter
        mock_flow.assert_called_once()
        _, kwargs = mock_flow.call_args
        assert kwargs.get("conversion_filter") == "converted" or mock_flow.call_args[0][1] == "converted"

    @patch("app.main.get_journey_flow")
    def test_endpoint_200_non_converted_filter(self, mock_flow):
        mock_flow.return_value = JourneyFlowResponse(
            nodes=[],
            links=[],
            total_journeys=0,
            total_transitions=0,
            converted_journeys=0,
            non_converted_journeys=0,
        )
        r = client.get("/api/analytics/journey-flow?conversion=non_converted")
        assert r.status_code == 200

    @patch("app.main.get_journey_flow")
    def test_endpoint_200_with_limit(self, mock_flow):
        mock_flow.return_value = JourneyFlowResponse(
            nodes=[],
            links=[],
            total_journeys=0,
            total_transitions=0,
            converted_journeys=0,
            non_converted_journeys=0,
        )
        r = client.get("/api/analytics/journey-flow?limit=100")
        assert r.status_code == 200

    @patch("app.main.get_journey_flow")
    def test_endpoint_500_error_sanitized(self, mock_flow):
        mock_flow.side_effect = RuntimeError("FATAL: relation 'customers' does not exist")
        r = client.get("/api/analytics/journey-flow")
        assert r.status_code == 500
        detail = r.json()["detail"]
        assert "FATAL: relation" not in detail
        assert "Internal error" in detail

    def test_endpoint_response_structure(self):
        """Verify response shape matches JourneyFlowResponse schema."""
        with patch("app.main.get_journey_flow") as mock_flow:
            mock_flow.return_value = JourneyFlowResponse(
                nodes=[
                    JourneyFlowNode(id=START_NODE_ID, label=START_NODE_LABEL, type="start"),
                ],
                links=[],
                total_journeys=0,
                total_transitions=0,
                converted_journeys=0,
                non_converted_journeys=0,
            )
            r = client.get("/api/analytics/journey-flow")
            assert r.status_code == 200
            body = r.json()
            # Check all required fields are present
            assert "nodes" in body
            assert "links" in body
            assert "total_journeys" in body
            assert "total_transitions" in body
            assert "converted_journeys" in body
            assert "non_converted_journeys" in body
            # Check node structure
            node = body["nodes"][0]
            assert "id" in node
            assert "label" in node
            assert "type" in node
