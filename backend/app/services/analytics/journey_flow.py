# -*- coding: utf-8 -*-
"""
backend/app/services/analytics/journey_flow.py

Journey Flow Graph Construction — Stage 7.

PURPOSE
-------
Build an aggregated directional flow graph showing how customers move
between marketing channels before (and through) conversion.

The graph answers: "How do customers move between channels before conversion?"

DESIGN DECISIONS
----------------
1. Reuses `fetch_all_journeys_from_db()` — same 3-query bulk loader used by
   journey patterns. We do NOT open new database connections or query per-customer.

2. Uses `journey.channels` (the authoritative channel path from journey_service).
   We do NOT re-derive channel paths here; we trust what build_journey() returns.

3. Non-consecutive repeated channels are PRESERVED as distinct transitions.
   Instagram → Google → Instagram → Email produces 3 separate transitions,
   not collapsed to Instagram → Google → Email.

4. Special node IDs use double-underscore prefix/suffix to avoid any collision
   with real channel names:
     __START__       → "Journey Start"
     __CONVERSION__  → "Conversion"

5. A START node is prepended to every journey so the graph shows which channels
   are acquisition channels (directly reachable from START) vs. intermediate.

6. CONVERSION node is appended only to converted journeys. Non-converted journeys
   terminate without a CONVERSION node — we do not invent a NULL/dropoff node.

7. Limit applies to the number of journeys included in flow construction,
   not to the number of links returned.

FLOW CONSTRUCTION ALGORITHM
----------------------------
For each journey with channel path [A, B, C] (converted):

  Augmented path: [__START__, A, B, C, __CONVERSION__]
  Transitions:    __START__ → A
                  A → B
                  B → C
                  C → __CONVERSION__

For a non-converted journey with path [A, B]:

  Augmented path: [__START__, A, B]
  Transitions:    __START__ → A
                  A → B

All identical (source, target) pairs are aggregated by summing their counts.
"""

import logging
from collections import defaultdict
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.services.analytics.journeys import fetch_all_journeys_from_db
from backend.app.services.journey_service import CustomerJourney

logger = logging.getLogger(__name__)


# =============================================================================
# Special node identifiers
# =============================================================================

START_NODE_ID: str = "__START__"
CONVERSION_NODE_ID: str = "__CONVERSION__"

START_NODE_LABEL: str = "Journey Start"
CONVERSION_NODE_LABEL: str = "Conversion"

ConversionFilter = Literal["all", "converted", "non_converted"]


# =============================================================================
# Pydantic response models
# =============================================================================

class JourneyFlowNode(BaseModel):
    """A node in the journey flow graph representing a channel or special state."""
    id: str = Field(..., description="Unique node identifier. Special nodes use __START__ and __CONVERSION__.")
    label: str = Field(..., description="Human-readable display label for the node.")
    type: str = Field(..., description="Node category: 'start', 'channel', or 'conversion'.")


class JourneyFlowLink(BaseModel):
    """A directed edge in the journey flow graph."""
    source: str = Field(..., description="Source node ID.")
    target: str = Field(..., description="Target node ID.")
    value: int = Field(..., description="Number of journeys that traversed this transition.")


class JourneyFlowResponse(BaseModel):
    """
    Complete journey flow graph for rendering.

    The `limit` parameter controls how many journeys are used to build the graph.
    It does NOT limit the number of links returned — all aggregated transitions
    from the included journeys are returned.
    """
    nodes: list[JourneyFlowNode] = Field(
        ...,
        description="All unique nodes (channels + special states) present in the graph.",
    )
    links: list[JourneyFlowLink] = Field(
        ...,
        description=(
            "Aggregated directed transitions. Sorted by value descending, "
            "then source ascending, then target ascending."
        ),
    )
    total_journeys: int = Field(..., description="Total journeys included in graph construction (after filtering).")
    total_transitions: int = Field(..., description="Total aggregated unique (source, target) pairs in the graph.")
    converted_journeys: int = Field(..., description="Number of converted journeys included in the graph.")
    non_converted_journeys: int = Field(..., description="Number of non-converted journeys included in the graph.")


# =============================================================================
# Pure flow construction (no DB dependency — independently testable)
# =============================================================================

def build_journey_flow(
    journeys: list[CustomerJourney],
    conversion_filter: ConversionFilter = "all",
    limit: int = 1000,
) -> JourneyFlowResponse:
    """
    Construct a directional flow graph from a collection of customer journeys.

    Parameters
    ----------
    journeys          : List of CustomerJourney objects (already built by journey_service).
    conversion_filter : One of "all", "converted", "non_converted".
                        Filters which journeys contribute to the graph.
    limit             : Maximum number of journeys to include in flow construction
                        (applied after filtering). Must be 1–5000.
                        Does NOT cap the number of links returned.

    Returns
    -------
    JourneyFlowResponse with nodes, links, and summary counts.

    Algorithm
    ---------
    1. Filter journeys by conversion_filter.
    2. Apply journey limit (first N after filtering).
    3. For each journey, build an augmented channel sequence:
         [__START__] + journey.channels + ([__CONVERSION__] if converted else [])
    4. Walk adjacent pairs in the augmented sequence → collect (source, target) pairs.
    5. Count occurrences of identical (source, target) pairs.
    6. Build node list from all unique IDs encountered.
    7. Sort links deterministically: value DESC, source ASC, target ASC.
    """
    # --- Step 1: Filter ---
    if conversion_filter == "converted":
        filtered = [j for j in journeys if j.converted]
    elif conversion_filter == "non_converted":
        filtered = [j for j in journeys if not j.converted]
    else:  # "all"
        filtered = list(journeys)

    # --- Step 2: Apply journey limit ---
    included = filtered[:limit]

    converted_count = sum(1 for j in included if j.converted)
    non_converted_count = len(included) - converted_count

    # --- Step 3 & 4: Build transition counts ---
    # transition_counts[(source, target)] = int
    transition_counts: dict[tuple[str, str], int] = defaultdict(int)

    for journey in included:
        # Skip journeys with no channel path (empty journeys produce no useful transitions)
        if not journey.channels:
            continue

        # Augmented path: START + channels + (CONVERSION if applicable)
        augmented: list[str] = [START_NODE_ID] + journey.channels
        if journey.converted:
            augmented.append(CONVERSION_NODE_ID)

        # Walk adjacent pairs
        for i in range(len(augmented) - 1):
            src = augmented[i]
            tgt = augmented[i + 1]
            transition_counts[(src, tgt)] += 1

    # --- Step 5: Collect all unique node IDs ---
    node_ids: set[str] = set()
    for (src, tgt) in transition_counts:
        node_ids.add(src)
        node_ids.add(tgt)

    # --- Step 6: Build node list ---
    def _node_type(nid: str) -> str:
        if nid == START_NODE_ID:
            return "start"
        if nid == CONVERSION_NODE_ID:
            return "conversion"
        return "channel"

    def _node_label(nid: str) -> str:
        if nid == START_NODE_ID:
            return START_NODE_LABEL
        if nid == CONVERSION_NODE_ID:
            return CONVERSION_NODE_LABEL
        return nid

    # Deterministic node order: __START__ first, channels alphabetically, __CONVERSION__ last
    def _node_sort_key(nid: str) -> tuple:
        if nid == START_NODE_ID:
            return (0, "")
        if nid == CONVERSION_NODE_ID:
            return (2, "")
        return (1, nid.lower())

    sorted_node_ids = sorted(node_ids, key=_node_sort_key)
    nodes = [
        JourneyFlowNode(id=nid, label=_node_label(nid), type=_node_type(nid))
        for nid in sorted_node_ids
    ]

    # --- Step 7: Build and sort links ---
    links = [
        JourneyFlowLink(source=src, target=tgt, value=count)
        for (src, tgt), count in transition_counts.items()
    ]
    # Deterministic sort: value DESC, source ASC, target ASC
    links.sort(key=lambda lk: (-lk.value, lk.source, lk.target))

    logger.debug(
        "Journey flow built: journeys=%d nodes=%d links=%d (filter=%s)",
        len(included),
        len(nodes),
        len(links),
        conversion_filter,
    )

    return JourneyFlowResponse(
        nodes=nodes,
        links=links,
        total_journeys=len(included),
        total_transitions=len(links),
        converted_journeys=converted_count,
        non_converted_journeys=non_converted_count,
    )


# =============================================================================
# Database-backed orchestration
# =============================================================================

def get_journey_flow(
    db,
    conversion_filter: ConversionFilter = "all",
    limit: int = 1000,
) -> JourneyFlowResponse:
    """
    Database-backed orchestration for journey flow graph construction.

    Loads all customer journeys in bulk (3 SQL queries total via
    fetch_all_journeys_from_db), then delegates to the pure
    build_journey_flow() function.

    Parameters
    ----------
    db                : SQLAlchemy database session
    conversion_filter : "all" | "converted" | "non_converted"
    limit             : Max journeys to include (1–5000)
    """
    journeys = fetch_all_journeys_from_db(db)
    logger.info(
        "Journey flow: loaded %d total journeys (filter=%s limit=%d)",
        len(journeys),
        conversion_filter,
        limit,
    )
    return build_journey_flow(journeys, conversion_filter=conversion_filter, limit=limit)
