# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/position_based.py

Position-Based (U-Shaped) Attribution Model.

CONCEPT
-------
Position-based attribution recognizes that both the first touchpoint (discovery)
and the last touchpoint (conversion decision) are disproportionately impactful,
while middle touchpoints provide supporting nurturing.

RULES & DEFAULT SPLIT
---------------------
- 1 touchpoint:
    100% to that channel.
- 2 touchpoints:
    50% to the first, 50% to the second.
- 3+ touchpoints:
    First touch: 40% (default, configurable)
    Last touch: 40% (default, configurable)
    Middle touches: remaining 20% divided equally across all (N - 2) middle touchpoints.

REPEATED CHANNELS
-----------------
If a channel appears at multiple positions (e.g. first and last, or middle and last),
it accumulates the credit from all positions it occupied.
Example: Instagram -> Google Search -> Instagram
- Touch 1 (Instagram): 40%
- Touch 2 (Google Search): 20%
- Touch 3 (Instagram): 40%
Final aggregated result:
- Instagram: 80% credit
- Google Search: 20% credit
Sum = 100% (1.0).
"""

from collections import OrderedDict
from backend.app.services.journey_service import CustomerJourney
from .models import AttributionCredit, AttributionResult


def calculate_position_based_attribution(
    journey: CustomerJourney,
    first_weight: float = 0.40,
    last_weight: float = 0.40,
) -> AttributionResult:
    """
    Calculate Position-Based (U-Shaped) attribution for a customer journey.

    Parameters:
        journey: CustomerJourney object
        first_weight: Weight assigned to the first touchpoint (default 0.40)
        last_weight: Weight assigned to the last touchpoint (default 0.40)

    Returns:
        AttributionResult with credits assigned according to position and
        aggregated by channel.
    """
    if not journey.converted or not journey.conversion_revenue or journey.conversion_revenue <= 0:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="position_based",
            conversion_revenue=0.0,
            credits=[],
            total_credit=0.0,
        )

    if not journey.channels:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="position_based",
            conversion_revenue=float(journey.conversion_revenue),
            credits=[],
            total_credit=0.0,
        )

    n = len(journey.channels)

    # Determine per-touchpoint raw weights
    if n == 1:
        raw_credits = [1.0]
    elif n == 2:
        raw_credits = [0.5, 0.5]
    else:
        # 3 or more touchpoints
        # Clamp first and last weights to valid ranges
        w_first = max(0.0, min(1.0, first_weight))
        w_last = max(0.0, min(1.0 - w_first, last_weight))
        w_middle_total = max(0.0, 1.0 - w_first - w_last)
        w_middle_each = w_middle_total / (n - 2)

        raw_credits = [w_first] + [w_middle_each] * (n - 2) + [w_last]

    # Aggregate by channel preserving order of first appearance
    channel_credits: OrderedDict[str, float] = OrderedDict()
    for ch, credit in zip(journey.channels, raw_credits):
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
        model="position_based",
        conversion_revenue=rev,
        credits=credits,
        total_credit=total_credit,
    )
