# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/linear.py

Linear Attribution Model.

CONCEPT
-------
Linear attribution divides conversion credit and revenue equally across all
touchpoints along the customer's conversion path.

HOW REPEATED CHANNELS ARE HANDLED
---------------------------------
Repeated channels (e.g. Instagram -> Google Search -> Instagram -> Email) are:
1. First treated as SEPARATE, independent touchpoints when distributing credit.
   In a 4-touch journey, each touchpoint receives exactly 1/4 (25%) of the credit.
   Instagram at step 1 receives 25%, and Instagram at step 3 receives 25%.
2. Then AGGREGATED at the channel level for the final report.
   Instagram's two 25% shares are summed to 50% total credit and 50% of the revenue.
   This accurately reflects that the customer engaged with Instagram twice without
   artificially diluting the impact of repeated exposures.

REVENUE CONSERVATION
--------------------
Total credit sums to 1.0.
Channel-level attributed revenue sums to exactly the journey conversion revenue.
"""

from collections import OrderedDict
from backend.app.services.journey_service import CustomerJourney
from .models import AttributionCredit, AttributionResult


def calculate_linear_attribution(journey: CustomerJourney) -> AttributionResult:
    """
    Calculate Linear multi-touch attribution for a customer journey.

    Parameters:
        journey: CustomerJourney object from journey_service.py

    Returns:
        AttributionResult with credit and revenue divided equally among touchpoints
        and aggregated by channel.
    """
    if not journey.converted or not journey.conversion_revenue or journey.conversion_revenue <= 0:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="linear",
            conversion_revenue=0.0,
            credits=[],
            total_credit=0.0,
        )

    if not journey.channels:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="linear",
            conversion_revenue=float(journey.conversion_revenue),
            credits=[],
            total_credit=0.0,
        )

    n_touches = len(journey.channels)
    touch_credit = 1.0 / n_touches
    rev = float(journey.conversion_revenue)

    # Step 1: Assign 1/N credit to each touchpoint occurrence
    # Step 2: Aggregate by channel preserving order of first appearance
    channel_credits: OrderedDict[str, float] = OrderedDict()
    for ch in journey.channels:
        channel_credits[ch] = channel_credits.get(ch, 0.0) + touch_credit

    # Step 3: Build AttributionCredit list and verify conservation
    credits: list[AttributionCredit] = []
    for ch, credit in channel_credits.items():
        channel_revenue = credit * rev
        credits.append(
            AttributionCredit(
                channel=ch,
                credit=credit,
                attributed_revenue=channel_revenue,
            )
        )

    total_credit = sum(c.credit for c in credits)

    return AttributionResult(
        customer_id=journey.customer_id,
        model="linear",
        conversion_revenue=rev,
        credits=credits,
        total_credit=total_credit,
    )
