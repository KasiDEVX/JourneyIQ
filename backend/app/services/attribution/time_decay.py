# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/time_decay.py

Time-Decay Attribution Model.

CONCEPT
-------
Time-decay attribution gives more credit to marketing touchpoints that occurred
closer in time to the conversion event, and progressively less credit to older
touchpoints.

MATHEMATICAL FORMULA
--------------------
For each touchpoint i with timestamp t_i:

    age = (t_conversion - t_i) in days
    weight_i = 0.5 ** (age / half_life)

Where:
- age is the time elapsed between the touchpoint and the conversion (in days).
- half_life is the period (in days) over which a touchpoint's credit drops by 50%.
  Default is 7.0 days (standard across Google Analytics & industry tools).
- Normalized credit:
    credit_i = weight_i / sum(weights)

REPEATED CHANNELS
-----------------
Each touchpoint occurrence receives its own timestamp-based weight.
When aggregating to channel level, all weights for that channel are summed.
For example, if Instagram appeared at day -14 (weight 0.25) and day 0 (weight 1.0),
Instagram receives credit for both appearances (0.25 + 1.0 = 1.25), which is then
normalized across all channels.
"""

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Union

from backend.app.services.journey_service import (
    CustomerJourney,
    JourneyEvent,
    TOUCHPOINT_EVENT_TYPES,
    NO_MARKETING_CHANNELS,
    _group_into_sessions,
)
from .models import AttributionCredit, AttributionResult


def _extract_touchpoint_timestamps(journey: CustomerJourney) -> list[tuple[str, datetime]]:
    """
    Extract (channel, timestamp) for each touchpoint in the journey.

    Replicates the exact touchpoint and deduplication rules used in journey_service.py:
    1. Direct marketing triggers (impression/click, first per channel per session)
    2. Marketing entry page_view at start of session
    3. Collapse consecutive duplicate channels

    If events are not available (e.g. synthetic test object), falls back to
    spacing touchpoints chronologically prior to conversion.
    """
    if journey.events:
        groups = _group_into_sessions(journey.events)
        raw: list[tuple[str, datetime]] = []

        for grp in groups:
            seen_in_session: set[str] = set()
            for i, ev in enumerate(grp):
                channel = ev.channel
                ev_type = ev.event_type
                is_first = (i == 0)

                if ev_type in TOUCHPOINT_EVENT_TYPES:
                    if channel not in seen_in_session:
                        raw.append((channel, ev.timestamp))
                        seen_in_session.add(channel)
                elif ev_type == "page_view" and is_first:
                    if channel not in NO_MARKETING_CHANNELS:
                        if channel not in seen_in_session:
                            raw.append((channel, ev.timestamp))
                            seen_in_session.add(channel)

        # Collapse consecutive duplicates preserving earliest timestamp of the run
        collapsed: list[tuple[str, datetime]] = []
        for ch, ts in raw:
            if not collapsed or collapsed[-1][0] != ch:
                collapsed.append((ch, ts))

        if len(collapsed) == len(journey.channels):
            return collapsed

    # Fallback for synthetic/mock journeys with missing or non-matching events
    ref_time = journey.conversion_timestamp or journey.last_activity or datetime.now(timezone.utc)
    n = len(journey.channels)
    # Space touchpoints 1 day apart backwards from conversion
    return [
        (ch, ref_time - timedelta(days=float(n - 1 - idx)))
        for idx, ch in enumerate(journey.channels)
    ]


def calculate_time_decay_attribution(
    journey: CustomerJourney,
    half_life: Union[float, int, timedelta] = 7.0,
) -> AttributionResult:
    """
    Calculate Time-Decay attribution for a customer journey.

    Parameters:
        journey: CustomerJourney object
        half_life: Half-life decay parameter (in days or as a timedelta, default=7.0 days).
                   A smaller half-life heavily favors the most recent touches.

    Returns:
        AttributionResult with exponential decay credits assigned to touchpoints
        and aggregated by channel.
    """
    if not journey.converted or not journey.conversion_revenue or journey.conversion_revenue <= 0:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="time_decay",
            conversion_revenue=0.0,
            credits=[],
            total_credit=0.0,
        )

    if not journey.channels:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="time_decay",
            conversion_revenue=float(journey.conversion_revenue),
            credits=[],
            total_credit=0.0,
        )

    # Convert half_life to float days
    if isinstance(half_life, timedelta):
        half_life_days = max(1e-5, half_life.total_seconds() / 86400.0)
    else:
        half_life_days = max(1e-5, float(half_life))

    conv_time = journey.conversion_timestamp or journey.last_activity
    touchpoints = _extract_touchpoint_timestamps(journey)

    # Compute raw decay weight for each touchpoint
    weights: list[float] = []
    for ch, ts in touchpoints:
        age_seconds = max(0.0, (conv_time - ts).total_seconds())
        age_days = age_seconds / 86400.0
        weight = 0.5 ** (age_days / half_life_days)
        weights.append(weight)

    sum_weights = sum(weights)
    if sum_weights <= 0:
        # Fallback to equal weighting if all weights vanished
        raw_credits = [1.0 / len(weights)] * len(weights)
    else:
        raw_credits = [w / sum_weights for w in weights]

    # Aggregate by channel preserving order of first appearance
    channel_credits: OrderedDict[str, float] = OrderedDict()
    for (ch, _), credit in zip(touchpoints, raw_credits):
        channel_credits[ch] = channel_credits.get(ch, 0.0) + credit

    rev = float(journey.conversion_revenue)
    credits: list[AttributionCredit] = []
    for ch, credit in channel_credits.items():
        credits.append(
            AttributionCredit(
                channel=ch,
                credit=credit,
                attributed_revenue=credit * rev,
            )
        )

    total_credit = sum(c.credit for c in credits)

    return AttributionResult(
        customer_id=journey.customer_id,
        model="time_decay",
        conversion_revenue=rev,
        credits=credits,
        total_credit=total_credit,
    )
