# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/__init__.py

Attribution Engine Package — Stage 4.

Exports:
- AttributionCredit: Pydantic model for individual channel allocation
- AttributionResult: Pydantic model for complete attribution calculation output
- Individual model functions:
    * calculate_first_touch_attribution
    * calculate_last_touch_attribution
    * calculate_linear_attribution
    * calculate_time_decay_attribution
    * calculate_position_based_attribution
    * calculate_markov_attribution
- Unified engine interface:
    * calculate_attribution
"""

from .models import AttributionCredit, AttributionResult
from .first_touch import calculate_first_touch_attribution
from .last_touch import calculate_last_touch_attribution
from .linear import calculate_linear_attribution
from .time_decay import calculate_time_decay_attribution
from .position_based import calculate_position_based_attribution
from .markov import calculate_markov_attribution
from .engine import calculate_attribution

__all__ = [
    "AttributionCredit",
    "AttributionResult",
    "calculate_first_touch_attribution",
    "calculate_last_touch_attribution",
    "calculate_linear_attribution",
    "calculate_time_decay_attribution",
    "calculate_position_based_attribution",
    "calculate_markov_attribution",
    "calculate_attribution",
]
