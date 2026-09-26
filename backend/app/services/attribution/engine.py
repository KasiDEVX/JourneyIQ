# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/engine.py

Unified Marketing Channel Attribution Engine.

Provides the primary public API for calculating attribution across all
supported attribution models:
- first_touch
- last_touch
- linear
- time_decay
- position_based
- markov

EXAMPLE USAGE
-------------
Single Journey:
    result = calculate_attribution(journey, model="linear")
    result = calculate_attribution(journey, model="position_based", first_weight=0.4, last_weight=0.4)
    result = calculate_attribution(journey, model="time_decay", half_life=7.0)

Cohort-level Markov Attribution:
    result = calculate_markov_attribution(journeys)
"""

from typing import Union, Sequence
from backend.app.services.journey_service import CustomerJourney
from .models import AttributionResult
from .first_touch import calculate_first_touch_attribution
from .last_touch import calculate_last_touch_attribution
from .linear import calculate_linear_attribution
from .time_decay import calculate_time_decay_attribution
from .position_based import calculate_position_based_attribution
from .markov import calculate_markov_attribution


SUPPORTED_MODELS = (
    "first_touch",
    "last_touch",
    "linear",
    "time_decay",
    "position_based",
    "markov",
)


def calculate_attribution(
    journey: CustomerJourney,
    model: str = "linear",
    **kwargs,
) -> AttributionResult:
    """
    Unified entry point for computing marketing attribution on a CustomerJourney.

    Parameters:
        journey: A structured CustomerJourney object from journey_service.py
        model: Name of the attribution model to use.
               Supported: 'first_touch', 'last_touch', 'linear',
                          'time_decay', 'position_based', 'markov'.
        **kwargs: Optional model-specific parameters:
                  - time_decay: half_life (float/int/timedelta, default=7.0 days)
                  - position_based: first_weight (float, default=0.4), last_weight (float, default=0.4)

    Returns:
        AttributionResult with credits and attributed revenue for each channel.

    Raises:
        ValueError: If an unsupported or invalid model name is requested.
    """
    if not isinstance(model, str):
        raise ValueError(
            f"Invalid model parameter type: expected string, got {type(model).__name__}. "
            f"Supported models are: {', '.join(SUPPORTED_MODELS)}."
        )

    model_clean = model.strip().lower()

    if model_clean == "first_touch":
        return calculate_first_touch_attribution(journey)
    elif model_clean == "last_touch":
        return calculate_last_touch_attribution(journey)
    elif model_clean == "linear":
        return calculate_linear_attribution(journey)
    elif model_clean == "time_decay":
        return calculate_time_decay_attribution(journey, **kwargs)
    elif model_clean == "position_based":
        return calculate_position_based_attribution(journey, **kwargs)
    elif model_clean == "markov":
        return calculate_markov_attribution([journey], customer_id=journey.customer_id, **kwargs)
    else:
        raise ValueError(
            f"Unknown attribution model: '{model}'. "
            f"Supported models are: {', '.join(SUPPORTED_MODELS)}."
        )
