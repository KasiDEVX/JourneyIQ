# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/models.py

Pydantic data models for Marketing Channel Attribution.

WHY PYDANTIC MODELS?
--------------------
1. Strict Validation: Ensures all credit scores and revenue sums are valid numbers.
2. Serialization: Automatically converts to JSON for FastAPI responses.
3. Clean Type Hinting: Provides autocompletion and IDE linting across services.
"""

from typing import Optional
from pydantic import BaseModel, Field


class AttributionCredit(BaseModel):
    """
    Attribution share and revenue allocated to a single marketing channel.

    Attributes:
        channel: Name of the marketing channel (e.g. 'Google Search', 'Facebook', 'Email').
        credit: Attribution share/weight, representing fractional credit (0.0 to 1.0).
        attributed_revenue: Dollar revenue allocated to this channel based on its credit.
    """
    channel: str = Field(..., description="Marketing channel name")
    credit: float = Field(..., description="Attribution fraction/weight between 0.0 and 1.0")
    attributed_revenue: float = Field(..., description="Conversion revenue attributed in currency units")


class AttributionResult(BaseModel):
    """
    Complete attribution output for an individual customer journey or multi-journey dataset.

    Attributes:
        customer_id: Customer ID for single-journey models, or 'aggregate' for Markov models across cohorts.
        model: Name of the attribution algorithm applied (e.g. 'first_touch', 'markov').
        conversion_revenue: Total conversion revenue being attributed (0.0 for non-converted).
        credits: List of AttributionCredit objects detailing each channel's contribution.
        total_credit: Sum of all channel credits (1.0 for converted journeys with channels, 0.0 otherwise).
    """
    customer_id: Optional[str] = Field(None, description="Customer UUID or 'aggregate' for cohort-level models")
    model: str = Field(..., description="Attribution model name")
    conversion_revenue: float = Field(..., description="Total conversion revenue being attributed")
    credits: list[AttributionCredit] = Field(default_factory=list, description="Per-channel attribution allocations")
    total_credit: float = Field(..., description="Sum of attribution credits across channels")

    def get_channel_credit(self, channel: str) -> float:
        """Helper to get credit share for a specific channel, or 0.0 if not present."""
        for c in self.credits:
            if c.channel == channel:
                return c.credit
        return 0.0

    def get_channel_revenue(self, channel: str) -> float:
        """Helper to get attributed revenue for a specific channel, or 0.0 if not present."""
        for c in self.credits:
            if c.channel == channel:
                return c.attributed_revenue
        return 0.0
