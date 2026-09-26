# -*- coding: utf-8 -*-
"""
backend/app/services/analytics/__init__.py

Analytics Service Package — Stage 5 + Stage 7.

Exports:
- Pydantic response models:
    * OverviewAnalytics
    * ChannelAnalytics
    * AttributionChannel
    * AttributionAnalytics
    * AttributionComparison
    * JourneyPattern
    * JourneyFlowNode        (Stage 7)
    * JourneyFlowLink        (Stage 7)
    * JourneyFlowResponse    (Stage 7)
- Pure calculation functions (no DB dependency):
    * calculate_overview_analytics
    * calculate_channel_analytics
    * calculate_attribution_analytics
    * calculate_attribution_comparison
    * calculate_journey_patterns
    * build_journey_flow     (Stage 7)
- Database orchestration functions:
    * fetch_all_journeys_from_db
    * get_overview_analytics
    * get_channel_analytics
    * get_attribution_analytics
    * get_attribution_comparison
    * get_journey_patterns
    * get_journey_flow       (Stage 7)
"""

from .models import (
    OverviewAnalytics,
    ChannelAnalytics,
    AttributionChannel,
    AttributionAnalytics,
    AttributionComparison,
    JourneyPattern,
)
from .overview import (
    calculate_overview_analytics,
    get_overview_analytics,
)
from .channels import (
    calculate_channel_analytics,
    get_channel_analytics,
)
from .attribution import (
    calculate_attribution_analytics,
    calculate_attribution_comparison,
    get_attribution_analytics,
    get_attribution_comparison,
)
from .journeys import (
    fetch_all_journeys_from_db,
    calculate_journey_patterns,
    get_journey_patterns,
)
from .journey_flow import (
    JourneyFlowNode,
    JourneyFlowLink,
    JourneyFlowResponse,
    build_journey_flow,
    get_journey_flow,
)

__all__ = [
    # Stage 5
    "OverviewAnalytics",
    "ChannelAnalytics",
    "AttributionChannel",
    "AttributionAnalytics",
    "AttributionComparison",
    "JourneyPattern",
    "calculate_overview_analytics",
    "calculate_channel_analytics",
    "calculate_attribution_analytics",
    "calculate_attribution_comparison",
    "calculate_journey_patterns",
    "fetch_all_journeys_from_db",
    "get_overview_analytics",
    "get_channel_analytics",
    "get_attribution_analytics",
    "get_attribution_comparison",
    "get_journey_patterns",
    # Stage 7 — Journey Flow
    "JourneyFlowNode",
    "JourneyFlowLink",
    "JourneyFlowResponse",
    "build_journey_flow",
    "get_journey_flow",
]
