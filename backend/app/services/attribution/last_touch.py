# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/last_touch.py

Last-Touch Attribution Model.

CONCEPT
-------
Last-Touch attribution gives 100% of the conversion credit and revenue to the
final marketing touchpoint encountered immediately prior to conversion.

WHY USE IT?
-----------
- Best for understanding which channels are best at closing or converting users
  (bottom-of-funnel decision triggers).
- Ignores earlier brand-building or nurturing touchpoints.

RULES
-----
1. Operates on a structured CustomerJourney.
2. If the customer did not convert (or conversion revenue <= 0), no credit or revenue is attributed.
3. If the journey has no marketing channels, no credit is attributed.
4. Otherwise, the final channel in journey.channels receives 100% credit (credit=1.0)
   and all conversion revenue.
"""

from backend.app.services.journey_service import CustomerJourney
from .models import AttributionCredit, AttributionResult


def calculate_last_touch_attribution(journey: CustomerJourney) -> AttributionResult:
    """
    Calculate Last-Touch attribution for a single customer journey.

    Parameters:
        journey: CustomerJourney object from journey_service.py

    Returns:
        AttributionResult with 100% credit assigned to the last marketing channel.
    """
    if not journey.converted or not journey.conversion_revenue or journey.conversion_revenue <= 0:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="last_touch",
            conversion_revenue=0.0,
            credits=[],
            total_credit=0.0,
        )

    if not journey.channels:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="last_touch",
            conversion_revenue=float(journey.conversion_revenue),
            credits=[],
            total_credit=0.0,
        )

    last_channel = journey.channels[-1]
    rev = float(journey.conversion_revenue)

    credits = [
        AttributionCredit(
            channel=last_channel,
            credit=1.0,
            attributed_revenue=rev,
        )
    ]

    return AttributionResult(
        customer_id=journey.customer_id,
        model="last_touch",
        conversion_revenue=rev,
        credits=credits,
        total_credit=1.0,
    )
