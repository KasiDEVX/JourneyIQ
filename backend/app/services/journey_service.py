# -*- coding: utf-8 -*-
"""
backend/app/services/journey_service.py

Customer Journey Engine — Stage 3.

WHY A SERVICE LAYER?
--------------------
Route functions in main.py handle HTTP concerns only:
  - parse URL parameters
  - return the correct HTTP status code
  - format the response

All actual business logic lives HERE, in a service module that has no
knowledge of HTTP at all. This separation makes the logic independently
testable — you can call build_journey() in a test without starting a
web server or connecting to a database.

WHAT THIS MODULE DOES
----------------------
1. Pydantic response models    — define the shape of the API response
2. Pure business logic         — sessionize, extract touchpoints, build journey
3. Database query functions    — fetch customer/events/conversion rows
4. Orchestration entry point   — get_customer_journey() wires it all together
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Standard 30-minute inactivity session gap (matches Google Analytics 4 default)
SESSION_GAP_MINUTES: int = 30

# These event types represent a direct marketing trigger (user responded to an ad)
TOUCHPOINT_EVENT_TYPES: frozenset[str] = frozenset({"impression", "click"})

# Channels where the user arrived by their own volition — NOT a paid touchpoint.
# A page_view on one of these channels at the start of a session is NOT
# counted as a marketing touchpoint.
NO_MARKETING_CHANNELS: frozenset[str] = frozenset({
    "Direct",
    "Organic Search",
    "Referral",
})


# =============================================================================
# Pydantic response models
# =============================================================================
# Pydantic models serve two purposes:
#   1. They validate data — if a field has the wrong type, Pydantic raises early.
#   2. FastAPI uses them to auto-generate OpenAPI/Swagger documentation.
#
# Optional[X] = the field can be None (Python equivalent of nullable).

class JourneyEvent(BaseModel):
    """
    One raw event as returned from the events table.
    This is the lowest-level object — one row = one event.
    """
    timestamp:   datetime
    session_id:  str           # original session_id from the database
    channel:     str
    campaign_id: Optional[str] = None   # NULL for organic/direct channels
    event_type:  str
    page:        Optional[str] = None
    product_id:  Optional[str] = None


class JourneySession(BaseModel):
    """
    One COMPUTED session.

    NOTE: This is re-computed from timestamps using the 30-minute rule,
    NOT the session_id stored in the database. The DB session_id was
    assigned by the data generator; real analytics always re-derive sessions
    from timestamps so the logic is consistent.
    """
    session_index:     int       # 1-based session number for this customer
    started_at:        datetime
    ended_at:          datetime
    duration_minutes:  float
    event_count:       int
    channels:          list[str] # unique channels seen, in order of first appearance


class CustomerJourney(BaseModel):
    """
    Full structured journey for one customer.
    Contains both summary metrics and the raw events/sessions.
    """
    customer_id:              str
    first_seen:               datetime
    last_activity:            datetime
    journey_duration_minutes: float
    event_count:              int
    session_count:            int
    touchpoint_count:         int      # marketing touchpoints (not raw event count)
    unique_channel_count:     int
    channels:                 list[str]  # ordered channel path (duplicates collapsed)
    converted:                bool
    conversion_timestamp:     Optional[datetime] = None
    conversion_revenue:       Optional[float]   = None
    conversion_order_id:      Optional[str]     = None
    sessions:                 list[JourneySession]
    events:                   list[JourneyEvent]


class JourneySummary(BaseModel):
    """
    Lightweight summary — no events or sessions lists.
    Returned by GET /api/customers/{id}/journey/summary.
    Useful for listing many customers without sending megabytes of event data.
    """
    customer_id:              str
    converted:                bool
    conversion_revenue:       Optional[float] = None
    journey_duration_minutes: float
    event_count:              int
    session_count:            int
    touchpoint_count:         int
    unique_channel_count:     int
    channels:                 list[str]


class CustomerProfile(BaseModel):
    """
    Summary representation of a customer for list views.
    Returned by GET /api/customers.
    """
    customer_id:              str
    first_seen:               datetime
    converted:                bool
    conversion_revenue:       Optional[float] = None
    event_count:              int = 0


# =============================================================================
# Core sessionization (private)
# =============================================================================

def _group_into_sessions(events: list[JourneyEvent]) -> list[list[JourneyEvent]]:
    """
    Split a sorted list of events into session groups.

    ALGORITHM
    ---------
    Walk through events in chronological order.
    Compare the timestamp of each event to the previous one.
    If the gap exceeds SESSION_GAP_MINUTES (30), close the current group
    and start a new one.

    This is the simplest correct implementation of session windowing.

    Example:
        10:00 impression   -|
        10:10 click         | same session (10-min gap)
        10:25 page_view    -|
                              <- 31-min gap -> NEW SESSION
        10:56 impression   -|
        11:00 click        -| same session (4-min gap)

    Returns:
        A list of event groups. Each group is a list of JourneyEvent.
        The groups are in chronological order.
        Events within each group are in chronological order.
    """
    if not events:
        return []

    groups: list[list[JourneyEvent]] = []
    current_group: list[JourneyEvent] = [events[0]]

    for i in range(1, len(events)):
        prev_ts = events[i - 1].timestamp
        curr_ts = events[i].timestamp
        gap_minutes = (curr_ts - prev_ts).total_seconds() / 60

        if gap_minutes > SESSION_GAP_MINUTES:
            # Close current session, start a new one
            groups.append(current_group)
            current_group = [events[i]]
        else:
            current_group.append(events[i])

    groups.append(current_group)  # don't forget the last group
    return groups


def _make_session_model(index: int, group: list[JourneyEvent]) -> JourneySession:
    """Build a JourneySession from one group of events."""
    started_at = group[0].timestamp
    ended_at   = group[-1].timestamp
    duration   = (ended_at - started_at).total_seconds() / 60

    # dict.fromkeys preserves insertion order and deduplicates
    unique_channels = list(dict.fromkeys(e.channel for e in group))

    return JourneySession(
        session_index    = index,
        started_at       = started_at,
        ended_at         = ended_at,
        duration_minutes = round(duration, 2),
        event_count      = len(group),
        channels         = unique_channels,
    )


# =============================================================================
# Public session function (used in tests)
# =============================================================================

def sessionize_events(events: list[JourneyEvent]) -> list[JourneySession]:
    """
    Public API: sessionize events and return JourneySession model objects.

    Events must be sorted by timestamp ascending (the DB query guarantees this;
    build_journey also sorts defensively before calling this).

    Called from build_journey() and directly testable from tests.
    """
    groups = _group_into_sessions(events)
    return [_make_session_model(i + 1, grp) for i, grp in enumerate(groups)]


# =============================================================================
# Touchpoint and channel path extraction (private + public)
# =============================================================================

def _extract_path_from_groups(groups: list[list[JourneyEvent]]) -> list[str]:
    """
    Build the ordered marketing channel path from pre-computed session groups.

    TOUCHPOINT RULES (detailed)
    ---------------------------
    We record a touchpoint when:

    Rule 1 — Direct marketing trigger:
        event_type is 'impression' or 'click'
        AND it is the first such event for this channel within the current session.
        Rationale: impression/click = user explicitly responded to an ad.
        We cap at one per channel per session to avoid inflation (10 Instagram
        impressions in a row = 1 touchpoint, not 10).

    Rule 2 — Re-entry via marketing channel:
        event_type is 'page_view'
        AND it is the FIRST event of the session (the user's entry event)
        AND the channel is NOT a no-marketing channel (Direct/Organic/Referral)
        Rationale: If the user's first action in a new session is a page_view
        on Email or Google Search, they re-entered through that channel even
        though there's no impression/click recorded. This is common when
        email click tracking fires a page_view instead of a click event.

    CONSECUTIVE DUPLICATE COLLAPSING
    ---------------------------------
    After collecting all touchpoints, we collapse consecutive duplicates.
    Example:
        Instagram, Instagram, Google Search, Instagram
        becomes
        Instagram, Google Search, Instagram

    We do NOT collapse non-consecutive duplicates — returning through
    Instagram twice (with another channel in between) is a valid multi-touch
    path that attribution models should see.
    """
    raw_touchpoints: list[str] = []

    for group in groups:
        seen_in_session: set[str] = set()

        for i, event in enumerate(group):
            channel    = event.channel
            event_type = event.event_type
            is_first   = (i == 0)

            # Rule 1: impression or click
            if event_type in TOUCHPOINT_EVENT_TYPES:
                if channel not in seen_in_session:
                    raw_touchpoints.append(channel)
                    seen_in_session.add(channel)

            # Rule 2: page_view as session entry on a marketing channel
            elif event_type == "page_view" and is_first:
                if channel not in NO_MARKETING_CHANNELS:
                    if channel not in seen_in_session:
                        raw_touchpoints.append(channel)
                        seen_in_session.add(channel)

    # Collapse consecutive duplicates in the final path
    path: list[str] = []
    for ch in raw_touchpoints:
        if not path or path[-1] != ch:
            path.append(ch)

    return path


def extract_channel_path(events: list[JourneyEvent]) -> list[str]:
    """
    Public API: extract the ordered channel path from a sorted event list.
    Independently callable from tests.
    """
    groups = _group_into_sessions(events)
    return _extract_path_from_groups(groups)


# =============================================================================
# Journey builder (pure, no DB)
# =============================================================================

def build_journey(
    customer_id:    str,
    first_seen:     datetime,
    events:         list[JourneyEvent],
    conversion_row: Optional[dict] = None,
) -> CustomerJourney:
    """
    Assemble a CustomerJourney from already-fetched data.

    WHY THIS FUNCTION IS PURE (no DB calls)
    ----------------------------------------
    This makes it trivially testable. A unit test can call build_journey()
    with hand-crafted events and verify the output without touching PostgreSQL.

    Parameters
    ----------
    customer_id     : customer UUID string
    first_seen      : timestamp from the customers table
    events          : list of JourneyEvent objects (will be sorted here defensively)
    conversion_row  : dict with keys 'timestamp', 'revenue', 'order_id'
                      or None if the customer has not converted
    """
    if isinstance(first_seen, str):
        first_seen = datetime.fromisoformat(first_seen)
    if hasattr(first_seen, "tzinfo") and first_seen.tzinfo is None:
        first_seen = first_seen.replace(tzinfo=timezone.utc)

    # Sort defensively — DB query already orders by timestamp, but be safe
    events = sorted(events, key=lambda e: e.timestamp)

    if not events:
        return CustomerJourney(
            customer_id              = customer_id,
            first_seen               = first_seen,
            last_activity            = first_seen,
            journey_duration_minutes = 0.0,
            event_count              = 0,
            session_count            = 0,
            touchpoint_count         = 0,
            unique_channel_count     = 0,
            channels                 = [],
            converted                = False,
            sessions                 = [],
            events                   = [],
        )

    last_activity            = events[-1].timestamp
    journey_duration_minutes = (last_activity - first_seen).total_seconds() / 60

    # Sessionize once — reuse the groups for both session models and path
    groups       = _group_into_sessions(events)
    sessions     = [_make_session_model(i + 1, grp) for i, grp in enumerate(groups)]
    channel_path = _extract_path_from_groups(groups)

    # Unique channels (ordered by first appearance across all events)
    unique_channels = list(dict.fromkeys(e.channel for e in events))

    converted = conversion_row is not None

    return CustomerJourney(
        customer_id              = customer_id,
        first_seen               = first_seen,
        last_activity            = last_activity,
        journey_duration_minutes = round(journey_duration_minutes, 2),
        event_count              = len(events),
        session_count            = len(sessions),
        touchpoint_count         = len(channel_path),
        unique_channel_count     = len(unique_channels),
        channels                 = channel_path,
        converted                = converted,
        conversion_timestamp     = conversion_row["timestamp"] if converted else None,
        conversion_revenue       = float(conversion_row["revenue"]) if converted else None,
        conversion_order_id      = conversion_row["order_id"] if converted else None,
        sessions                 = sessions,
        events                   = events,
    )


# =============================================================================
# Database query functions
# =============================================================================
# Each function has a single responsibility: query one table, return plain dicts
# or model objects. They use SQLAlchemy's text() for raw SQL — readable,
# no ORM magic, and consistent with how load_data.py works.

def fetch_customer(customer_id: str, db) -> Optional[dict]:
    """
    Return {customer_id, first_seen} from the customers table, or None.
    None means the customer doesn't exist -> caller returns HTTP 404.
    """
    row = db.execute(
        text("""
            SELECT customer_id, first_seen
            FROM customers
            WHERE customer_id = :cid
        """),
        {"cid": customer_id},
    ).fetchone()

    if row is None:
        return None

    ts = row[1]
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if hasattr(ts, "tzinfo") and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return {"customer_id": row[0], "first_seen": ts}


def fetch_events_from_db(customer_id: str, db) -> list[JourneyEvent]:
    """
    Fetch all events for a customer sorted ascending by timestamp.
    Converts raw psycopg2 row tuples into typed JourneyEvent objects.
    """
    rows = db.execute(
        text("""
            SELECT timestamp, session_id, channel, campaign_id,
                   event_type, page, product_id
            FROM events
            WHERE customer_id = :cid
            ORDER BY timestamp ASC
        """),
        {"cid": customer_id},
    ).fetchall()

    events = []
    for row in rows:
        ts = row[0]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if hasattr(ts, "tzinfo") and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        events.append(JourneyEvent(
            timestamp   = ts,
            session_id  = row[1],
            channel     = row[2],
            campaign_id = row[3] or None,    # convert empty string -> None
            event_type  = row[4],
            page        = row[5] or None,
            product_id  = row[6] or None,
        ))

    logger.debug("Fetched %d events for customer %s", len(events), customer_id)
    return events


def fetch_conversion_from_db(customer_id: str, db) -> Optional[dict]:
    """
    Return the most recent conversion for a customer, or None.
    We fetch the most recent because a customer could theoretically purchase
    multiple times — attribution models will handle multi-conversion scenarios
    in Stage 4.
    """
    row = db.execute(
        text("""
            SELECT timestamp, revenue, order_id
            FROM conversions
            WHERE customer_id = :cid
            ORDER BY timestamp DESC
            LIMIT 1
        """),
        {"cid": customer_id},
    ).fetchone()

    if row is None:
        return None

    ts = row[0]
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    if hasattr(ts, "tzinfo") and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return {
        "timestamp": ts,
        "revenue":   float(row[1]),
        "order_id":  row[2],
    }


# =============================================================================
# Orchestration entry point
# =============================================================================

def get_customer_journey(customer_id: str, db) -> Optional[CustomerJourney]:
    """
    Top-level function called by the API route.

    1. Checks the customer exists -> None means 404
    2. Fetches events and conversion from DB
    3. Delegates to build_journey() for the actual logic

    Returns None if customer not found.
    """
    logger.info("Journey request for customer_id=%s", customer_id)

    customer = fetch_customer(customer_id, db)
    if customer is None:
        logger.warning("Customer not found: %s", customer_id)
        return None

    events     = fetch_events_from_db(customer_id, db)
    conversion = fetch_conversion_from_db(customer_id, db)

    logger.info(
        "customer=%s events=%d converted=%s",
        customer_id, len(events), conversion is not None,
    )

    first_seen = customer["first_seen"]

    return build_journey(
        customer_id    = customer_id,
        first_seen     = first_seen,
        events         = events,
        conversion_row = conversion,
    )


def fetch_customers_list(
    db,
    limit: int = 50,
    search: Optional[str] = None,
    converted: Optional[bool] = None,
) -> list[CustomerProfile]:
    """
    Fetch a paginated list of customers with conversion status and event count.
    Supports filtering by search query (customer_id substring) and conversion state.
    """
    where_clauses = []
    params: dict = {"limit": limit}

    if search:
        clean_search = re.sub(r"[^a-zA-Z0-9\-]", "", search.strip())
        if clean_search:
            where_clauses.append("LOWER(c.customer_id) LIKE :search")
            params["search"] = f"%{clean_search.lower()}%"

    if converted is True:
        where_clauses.append("conv.customer_id IS NOT NULL")
    elif converted is False:
        where_clauses.append("conv.customer_id IS NULL")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    sql = text(f"""
        SELECT 
            c.customer_id, 
            c.first_seen,
            CASE WHEN conv.customer_id IS NOT NULL THEN 1 ELSE 0 END as converted,
            conv.revenue as conversion_revenue,
            COUNT(e.timestamp) as event_count
        FROM customers c
        LEFT JOIN conversions conv ON c.customer_id = conv.customer_id
        LEFT JOIN events e ON c.customer_id = e.customer_id
        {where_sql}
        GROUP BY c.customer_id, c.first_seen, conv.customer_id, conv.revenue
        ORDER BY converted DESC, c.first_seen DESC
        LIMIT :limit
    """)

    rows = db.execute(sql, params).fetchall()
    result = []
    for r in rows:
        ts = r[1]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if hasattr(ts, "tzinfo") and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        result.append(CustomerProfile(
            customer_id=r[0],
            first_seen=ts,
            converted=bool(r[2]),
            conversion_revenue=float(r[3]) if r[3] is not None else None,
            event_count=int(r[4]),
        ))
    return result

