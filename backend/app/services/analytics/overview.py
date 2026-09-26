# -*- coding: utf-8 -*-
"""
backend/app/services/analytics/overview.py

Overview Analytics Service.

CALCULATED METRICS
------------------
- customers: Count of unique customers evaluated.
- events: Total interaction events across all journeys.
- sessions: Total sessions windowed across all journeys.
- conversions: Count of customers who completed a purchase.
- conversion_rate: conversions / customers (guarded against division by zero).
- total_revenue: Sum of conversion revenues.
- average_order_value: total_revenue / conversions (guarded against division by zero).
- average_journey_duration_minutes: Mean journey duration across customers.
- average_touchpoints: Mean marketing touchpoints per customer.
- unique_channels: Distinct channels observed across all customer interactions.
"""

import logging
from backend.app.services.journey_service import CustomerJourney
from .models import OverviewAnalytics
from .journeys import fetch_all_journeys_from_db

logger = logging.getLogger(__name__)


def calculate_overview_analytics(journeys: list[CustomerJourney]) -> OverviewAnalytics:
    """
    Pure analytics calculation: aggregates cohort KPIs from a list of CustomerJourneys.

    Parameters:
        journeys: List of CustomerJourney objects

    Returns:
        OverviewAnalytics model populated with verified summary statistics.
    """
    customers_count = len(journeys)
    if customers_count == 0:
        return OverviewAnalytics(
            customers=0,
            events=0,
            sessions=0,
            conversions=0,
            conversion_rate=0.0,
            total_revenue=0.0,
            average_order_value=0.0,
            average_journey_duration_minutes=0.0,
            average_touchpoints=0.0,
            unique_channels=0,
        )

    events_count = sum(j.event_count for j in journeys)
    sessions_count = sum(j.session_count for j in journeys)

    converting_journeys = [
        j for j in journeys
        if j.converted and j.conversion_revenue is not None and j.conversion_revenue > 0
    ]
    conversions_count = len(converting_journeys)

    total_revenue = sum(float(j.conversion_revenue) for j in converting_journeys)

    # Conversion rate and AOV
    conversion_rate = conversions_count / customers_count if customers_count > 0 else 0.0
    aov = total_revenue / conversions_count if conversions_count > 0 else 0.0

    # Journey duration and touchpoint averages
    total_duration = sum(j.journey_duration_minutes for j in journeys)
    avg_duration = total_duration / customers_count if customers_count > 0 else 0.0

    total_touchpoints = sum(j.touchpoint_count for j in journeys)
    avg_touchpoints = total_touchpoints / customers_count if customers_count > 0 else 0.0

    # Collect unique channels seen across events and channel paths
    channels_set: set[str] = set()
    for j in journeys:
        channels_set.update(j.channels)
        for ev in j.events:
            if ev.channel:
                channels_set.add(ev.channel)

    return OverviewAnalytics(
        customers=customers_count,
        events=events_count,
        sessions=sessions_count,
        conversions=conversions_count,
        conversion_rate=round(conversion_rate, 4),
        total_revenue=round(total_revenue, 2),
        average_order_value=round(aov, 2),
        average_journey_duration_minutes=round(avg_duration, 2),
        average_touchpoints=round(avg_touchpoints, 2),
        unique_channels=len(channels_set),
    )


def get_overview_analytics(db) -> OverviewAnalytics:
    """
    Database-backed orchestration function for overview analytics.
    """
    journeys = fetch_all_journeys_from_db(db)
    return calculate_overview_analytics(journeys)
