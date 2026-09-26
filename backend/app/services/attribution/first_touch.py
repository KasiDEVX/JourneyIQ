# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/first_touch.py

First-Touch Attribution Model.

CONCEPT
-------
First-Touch attribution gives 100% of the conversion credit and revenue to the
very first marketing touchpoint a customer encountered.

WHY USE IT?
-----------
- Best for understanding which channels are best at acquiring new prospective customers
  (top-of-funnel brand awareness and initial discovery).
- Overlooks subsequent nurturing and closing touchpoints.

RULES
-----
1. Operates on a structured CustomerJourney.
2. If the customer did not convert (or conversion revenue <= 0), no credit or revenue is attributed.
3. If the journey has no marketing channels, no credit is attributed.
4. Otherwise, the first channel in journey.channels receives 100% credit (credit=1.0)
   and all conversion revenue.
"""

from backend.app.services.journey_service import CustomerJourney
from .models import AttributionCredit, AttributionResult


def calculate_first_touch_attribution(journey: CustomerJourney) -> AttributionResult:
    """
    Calculate First-Touch attribution for a single customer journey.

    Parameters:
        journey: CustomerJourney object from journey_service.py

    Returns:
        AttributionResult with 100% credit assigned to the first marketing channel.
    """
    if not journey.converted or not journey.conversion_revenue or journey.conversion_revenue <= 0:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="first_touch",
            conversion_revenue=0.0,
            credits=[],
            total_credit=0.0,
        )

    if not journey.channels:
        return AttributionResult(
            customer_id=journey.customer_id,
            model="first_touch",
            conversion_revenue=float(journey.conversion_revenue),
            credits=[],
            total_credit=0.0,
        )

    first_channel = journey.channels[0]
    rev = float(journey.conversion_revenue)

    credits = [
        AttributionCredit(
            channel=first_channel,
            credit=1.0,
            attributed_revenue=rev,
        )
    ]

    return AttributionResult(
        customer_id=journey.customer_id,
        model="first_touch",
        conversion_revenue=rev,
        credits=credits,
        total_credit=1.0,
    )
