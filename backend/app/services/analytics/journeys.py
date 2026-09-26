# -*- coding: utf-8 -*-
"""
backend/app/services/analytics/journeys.py

Journey Pattern Analysis & Bulk Journey Loader.

WHY BULK LOADING INSTEAD OF INDIVIDUAL QUERIES?
----------------------------------------------
Fetching journeys for 500 customers one-by-one causes an N+1 query problem
(500 * 3 = 1500 queries). `fetch_all_journeys_from_db()` executes exactly 3 SQL
queries in total (customers, events, conversions), groups records in-memory,
and builds CustomerJourney objects in milliseconds.

JOURNEY PATTERN GROUPING
------------------------
Customer journeys are grouped by their exact ordered channel path (`journey.channels`).
- Non-consecutive repeated channels are preserved (e.g., Instagram -> Google -> Instagram).
- Consecutive duplicate channels remain collapsed (per JourneyService rules).
- Results are sorted deterministically: revenue DESC, customers DESC, path ASC.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from backend.app.services.journey_service import (
    CustomerJourney,
    JourneyEvent,
    build_journey,
)
from .models import JourneyPattern

logger = logging.getLogger(__name__)


def fetch_all_journeys_from_db(db) -> list[CustomerJourney]:
    """
    Fetch all customer journeys from PostgreSQL using exactly 3 bulk queries.

    Parameters:
        db: SQLAlchemy database session

    Returns:
        List of CustomerJourney objects for all customers in the database.
    """
    # 1. Fetch all customers
    cust_rows = db.execute(
        text("SELECT customer_id, first_seen FROM customers ORDER BY first_seen ASC")
    ).fetchall()

    if not cust_rows:
        return []

    # 2. Fetch all events sorted by customer and timestamp
    event_rows = db.execute(
        text("""
            SELECT customer_id, timestamp, session_id, channel, campaign_id,
                   event_type, page, product_id
            FROM events
            ORDER BY customer_id, timestamp ASC
        """)
    ).fetchall()

    events_by_customer: dict[str, list[JourneyEvent]] = defaultdict(list)
    for row in event_rows:
        cid = row[0]
        ts = row[1]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if hasattr(ts, "tzinfo") and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        events_by_customer[cid].append(
            JourneyEvent(
                timestamp=ts,
                session_id=row[2],
                channel=row[3],
                campaign_id=row[4] or None,
                event_type=row[5],
                page=row[6] or None,
                product_id=row[7] or None,
            )
        )

    # 3. Fetch all conversions (latest conversion per customer)
    conv_rows = db.execute(
        text("""
            SELECT customer_id, timestamp, revenue, order_id
            FROM conversions
            ORDER BY customer_id, timestamp DESC
        """)
    ).fetchall()

    conversions_by_customer: dict[str, dict] = {}
    for row in conv_rows:
        cid = row[0]
        if cid not in conversions_by_customer:  # keeps latest conversion
            ts = row[1]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            if hasattr(ts, "tzinfo") and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            conversions_by_customer[cid] = {
                "timestamp": ts,
                "revenue": float(row[2]),
                "order_id": row[3],
            }

    # 4. Construct CustomerJourney models
    journeys: list[CustomerJourney] = []
    for row in cust_rows:
        cid = row[0]
        fs = row[1]
        if isinstance(fs, str):
            fs = datetime.fromisoformat(fs)
        if hasattr(fs, "tzinfo") and fs.tzinfo is None:
            fs = fs.replace(tzinfo=timezone.utc)

        cust_events = events_by_customer.get(cid, [])
        conv_row = conversions_by_customer.get(cid, None)

        journey = build_journey(
            customer_id=cid,
            first_seen=fs,
            events=cust_events,
            conversion_row=conv_row,
        )
        journeys.append(journey)

    logger.debug("Reconstructed %d customer journeys in bulk", len(journeys))
    return journeys


def calculate_journey_patterns(
    journeys: list[CustomerJourney],
    limit: int = 20,
) -> list[JourneyPattern]:
    """
    Group customer journeys by their ordered channel sequence and calculate conversion metrics.

    Parameters:
        journeys: Collection of CustomerJourney objects
        limit: Maximum number of patterns to return (must be between 1 and 1000)

    Returns:
        List of JourneyPattern objects sorted by revenue DESC, customers DESC.
    """
    if limit is None or not isinstance(limit, int) or limit < 1 or limit > 1000:
        raise ValueError("Limit must be an integer between 1 and 1000.")

    if not journeys:
        return []

    # Path tuple -> list of journeys following that exact path
    path_groups: dict[tuple[str, ...], list[CustomerJourney]] = defaultdict(list)
    for j in journeys:
        path_key = tuple(j.channels)
        path_groups[path_key].append(j)

    patterns: list[JourneyPattern] = []

    for path_key, group in path_groups.items():
        total_customers = len(group)
        converting_customers = [j for j in group if j.converted]
        conversions_count = len(converting_customers)
        conv_rate = conversions_count / total_customers if total_customers > 0 else 0.0

        revenue = sum(
            float(j.conversion_revenue)
            for j in converting_customers
            if j.conversion_revenue is not None
        )

        avg_duration = (
            sum(j.journey_duration_minutes for j in group) / total_customers
            if total_customers > 0 else 0.0
        )
        avg_touchpoints = (
            sum(j.touchpoint_count for j in group) / total_customers
            if total_customers > 0 else 0.0
        )

        patterns.append(
            JourneyPattern(
                path=list(path_key),
                customers=total_customers,
                conversions=conversions_count,
                conversion_rate=round(conv_rate, 4),
                revenue=round(revenue, 2),
                average_journey_duration_minutes=round(avg_duration, 2),
                average_touchpoints=round(avg_touchpoints, 2),
            )
        )

    # Sort deterministically: revenue DESC, then customers DESC, then path string
    patterns.sort(key=lambda p: (-p.revenue, -p.customers, " > ".join(p.path)))

    return patterns[:limit]


def get_journey_patterns(db, limit: int = 20) -> list[JourneyPattern]:
    """
    Database-backed orchestration function for journey pattern analysis.
    """
    journeys = fetch_all_journeys_from_db(db)
    return calculate_journey_patterns(journeys, limit=limit)
