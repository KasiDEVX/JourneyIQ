# -*- coding: utf-8 -*-
"""
backend/app/services/analytics/attribution.py

Attribution Analytics & Multi-Model Comparison Service.

ROLES & RESPONSIBILITIES
------------------------
1. Reuses the core Attribution Engine from Stage 4 as the single source of truth.
2. For non-Markov models (first_touch, last_touch, linear, time_decay, position_based):
   - Computes attribution per converted customer journey.
   - Aggregates channel revenues and calculates overall cohort credit fractions.
   - Guarantees exact revenue conservation.
3. For Markov models:
   - Evaluates the batch Markov removal-effect algorithm across the journey collection.
4. Generates multi-model comparative analyses for visualization and charting.
"""

from collections import defaultdict
import logging
from typing import Optional

from backend.app.services.journey_service import CustomerJourney
from backend.app.services.attribution import (
    calculate_attribution,
    calculate_markov_attribution,
)
from .models import (
    AttributionChannel,
    AttributionAnalytics,
    AttributionComparison,
)
from .journeys import fetch_all_journeys_from_db

logger = logging.getLogger(__name__)

SUPPORTED_MODELS = (
    "first_touch",
    "last_touch",
    "linear",
    "time_decay",
    "position_based",
    "markov",
)


def calculate_attribution_analytics(
    journeys: list[CustomerJourney],
    model: str = "linear",
    **kwargs,
) -> AttributionAnalytics:
    """
    Calculate aggregated attribution across a collection of customer journeys.

    Parameters:
        journeys: Collection of CustomerJourney objects
        model: Attribution model name
        **kwargs: Optional model parameters (e.g. half_life, first_weight)

    Returns:
        AttributionAnalytics object with channel credits and attributed revenue.

    Raises:
        ValueError: If model name is unrecognized.
    """
    if not isinstance(model, str):
        raise ValueError(
            f"Invalid model parameter type: expected string, got {type(model).__name__}. "
            f"Supported models: {', '.join(SUPPORTED_MODELS)}."
        )

    model_clean = model.strip().lower()
    if model_clean not in SUPPORTED_MODELS:
        raise ValueError(
            f"Invalid attribution model: '{model}'. "
            f"Supported models are: {', '.join(SUPPORTED_MODELS)}."
        )

    converted_journeys = [
        j for j in journeys
        if j.converted and (j.conversion_revenue is not None) and (j.conversion_revenue > 0)
    ]
    total_revenue = sum(float(j.conversion_revenue) for j in converted_journeys)

    if not converted_journeys or total_revenue <= 0:
        return AttributionAnalytics(
            model=model_clean,
            total_revenue=0.0,
            channels=[],
        )

    # Markov model executes in batch across journeys
    if model_clean == "markov":
        markov_res = calculate_markov_attribution(journeys, **kwargs)
        channels = [
            AttributionChannel(
                channel=c.channel,
                credit=round(c.credit, 4),
                attributed_revenue=round(c.attributed_revenue, 2),
            )
            for c in markov_res.credits
        ]
        # Revenue conservation penny balance adjustment
        if channels:
            rev_diff = round(round(markov_res.conversion_revenue, 2) - sum(c.attributed_revenue for c in channels), 2)
            if abs(rev_diff) > 0:
                channels[0].attributed_revenue = round(channels[0].attributed_revenue + rev_diff, 2)

        channels.sort(key=lambda c: (-c.attributed_revenue, c.channel))
        return AttributionAnalytics(
            model="markov",
            total_revenue=round(markov_res.conversion_revenue, 2),
            channels=channels,
        )

    # Non-Markov models: calculate per converted journey and aggregate
    channel_attributed_rev: dict[str, float] = defaultdict(float)

    for j in converted_journeys:
        result = calculate_attribution(j, model=model_clean, **kwargs)
        for credit in result.credits:
            channel_attributed_rev[credit.channel] += credit.attributed_revenue

    channels = []
    for ch, rev in channel_attributed_rev.items():
        channel_credit = rev / total_revenue if total_revenue > 0 else 0.0
        channels.append(
            AttributionChannel(
                channel=ch,
                credit=round(channel_credit, 4),
                attributed_revenue=round(rev, 2),
            )
        )

    # Sort channels by attributed_revenue DESC
    channels.sort(key=lambda c: (-c.attributed_revenue, c.channel))

    # Revenue conservation penny balance adjustment
    if channels:
        tot_rev_rounded = round(total_revenue, 2)
        rev_diff = round(tot_rev_rounded - sum(c.attributed_revenue for c in channels), 2)
        if abs(rev_diff) > 0:
            channels[0].attributed_revenue = round(channels[0].attributed_revenue + rev_diff, 2)

    return AttributionAnalytics(
        model=model_clean,
        total_revenue=round(total_revenue, 2),
        channels=channels,
    )


def calculate_attribution_comparison(
    journeys: list[CustomerJourney],
) -> AttributionComparison:
    """
    Run all six attribution models over the same journey collection for comparison.

    Parameters:
        journeys: Collection of CustomerJourney objects

    Returns:
        AttributionComparison with all models populated.
    """
    converted_journeys = [
        j for j in journeys
        if j.converted and (j.conversion_revenue is not None) and (j.conversion_revenue > 0)
    ]
    total_rev = round(sum(float(j.conversion_revenue) for j in converted_journeys), 2)

    models_dict: dict[str, list[AttributionChannel]] = {}
    for m in SUPPORTED_MODELS:
        attr_result = calculate_attribution_analytics(journeys, model=m)
        models_dict[m] = attr_result.channels

    return AttributionComparison(
        models=models_dict,
        total_revenue=total_rev,
    )


def get_attribution_analytics(db, model: str = "linear", **kwargs) -> AttributionAnalytics:
    """
    Database-backed orchestration function for single-model attribution.
    """
    journeys = fetch_all_journeys_from_db(db)
    return calculate_attribution_analytics(journeys, model=model, **kwargs)


def get_attribution_comparison(db) -> AttributionComparison:
    """
    Database-backed orchestration function for multi-model attribution comparison.
    """
    journeys = fetch_all_journeys_from_db(db)
    return calculate_attribution_comparison(journeys)
