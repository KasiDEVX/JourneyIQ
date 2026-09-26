# -*- coding: utf-8 -*-
"""
backend/app/services/analytics/channels.py

Channel Performance Analytics Service.

CHANNEL METRICS DEFINITIONS
---------------------------
- channel: Marketing channel identifier.
- customers: Unique customers who engaged with this channel (each customer counted at most once per channel).
- events: Total events recorded under this channel across all journeys.
- sessions: Total sessions where this channel was encountered (derived from journey sessionization).
- conversions: Unique converted customers whose journey touched this channel (represents channel participation,
  independent of any fractional attribution model).
- conversion_rate: conversions / customers (guarded against division by zero).
- revenue: Total conversion revenue from converted customers who touched this channel.
- average_revenue: revenue / conversions (average order value per converting customer for this channel).
"""

from collections import defaultdict
import logging
from backend.app.services.journey_service import CustomerJourney
from .models import ChannelAnalytics
from .journeys import fetch_all_journeys_from_db

logger = logging.getLogger(__name__)


def calculate_channel_analytics(journeys: list[CustomerJourney]) -> list[ChannelAnalytics]:
    """
    Pure analytics calculation: aggregates channel-level engagement and conversion metrics.

    Parameters:
        journeys: Collection of CustomerJourney objects

    Returns:
        List of ChannelAnalytics objects sorted by revenue DESC, then customers DESC.
    """
    if not journeys:
        return []

    # Track all observed channels
    all_channels: set[str] = set()
    for j in journeys:
        all_channels.update(j.channels)
        for ev in j.events:
            if ev.channel:
                all_channels.add(ev.channel)

    channel_customers: dict[str, set[str]] = defaultdict(set)
    channel_events: dict[str, int] = defaultdict(int)
    channel_sessions: dict[str, int] = defaultdict(int)
    channel_conversions: dict[str, set[str]] = defaultdict(set)
    channel_revenue: dict[str, float] = defaultdict(float)

    for j in journeys:
        cid = j.customer_id
        is_converted = j.converted and (j.conversion_revenue is not None) and (j.conversion_revenue > 0)
        j_rev = float(j.conversion_revenue) if is_converted else 0.0

        # Unique channels touched in this customer's journey
        j_channels = set(j.channels)
        for ev in j.events:
            if ev.channel:
                j_channels.add(ev.channel)

        for ch in j_channels:
            channel_customers[ch].add(cid)
            if is_converted:
                channel_conversions[ch].add(cid)
                channel_revenue[ch] += j_rev

        # Total event count per channel
        for ev in j.events:
            if ev.channel:
                channel_events[ev.channel] += 1

        # Sessions containing this channel
        for sess in j.sessions:
            for ch in sess.channels:
                channel_sessions[ch] += 1

    results: list[ChannelAnalytics] = []

    for ch in all_channels:
        cust_count = len(channel_customers[ch])
        conv_count = len(channel_conversions[ch])
        ev_count = channel_events[ch]
        sess_count = channel_sessions[ch]
        rev = channel_revenue[ch]

        conv_rate = conv_count / cust_count if cust_count > 0 else 0.0
        avg_rev = rev / conv_count if conv_count > 0 else 0.0

        results.append(
            ChannelAnalytics(
                channel=ch,
                customers=cust_count,
                events=ev_count,
                sessions=sess_count,
                conversions=conv_count,
                conversion_rate=round(conv_rate, 4),
                revenue=round(rev, 2),
                average_revenue=round(avg_rev, 2),
            )
        )

    # Sort deterministically: revenue DESC, then customers DESC, then channel name ASC
    results.sort(key=lambda c: (-c.revenue, -c.customers, c.channel))

    return results


def get_channel_analytics(db) -> list[ChannelAnalytics]:
    """
    Database-backed orchestration function for channel performance analytics.
    """
    journeys = fetch_all_journeys_from_db(db)
    return calculate_channel_analytics(journeys)
