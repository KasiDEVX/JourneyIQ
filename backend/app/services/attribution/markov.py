# -*- coding: utf-8 -*-
"""
backend/app/services/attribution/markov.py

Markov Chain Multi-Touch Attribution with Removal Effect.

MATHEMATICAL FOUNDATION & ALGORITHM
====================================
A customer journey can be modeled as a discrete-time Markov chain where the
customer moves through states until reaching an absorbing state (CONVERSION or NULL).

1. State Space:
   - "START": The entry state before any marketing interaction.
   - Channel States (c_1, c_2, ..., c_m): Each unique marketing channel.
   - "CONVERSION": The absorbing state representing a successful conversion.
   - "NULL": The absorbing state representing customer abandonment / non-conversion.

2. Transition Probabilities:
   Across all observed journeys, we count the transitions between consecutive states:
   N(i, j) = number of times a transition from state i to state j was observed.
   The transition probability is:
       T(i, j) = N(i, j) / sum_k N(i, k)

3. Absorbing Markov Chain Conversion Probability:
   Partition states into Transient states T = [START, c_1, ..., c_m] and
   Absorbing states A = [CONVERSION, (NULL)].
   Let:
     Q = |T| x |T| transition matrix among transient states.
     r = |T| x 1 vector of transition probabilities directly to CONVERSION.

   The probability x_s of eventually reaching CONVERSION from any transient state s
   satisfies the system of linear equations:
       x_s = sum_{s' in T} Q(s, s') * x_s' + r_s
       (I - Q) * x = r
       x = (I - Q)^(-1) * r

   Baseline conversion probability from START:
       P_baseline = x[START]

4. Removal Effect:
   To evaluate the true incremental value of channel c, we simulate its removal
   from the marketing ecosystem:
   - Any customer entering channel c drops out (fails to reach CONVERSION).
   - In matrix terms, we zero out the transitions from state c:
     Q'[c, :] = 0 and r'[c] = 0.
   - We solve (I - Q') * x' = r' to obtain the new conversion probability:
     P_without_c = x'[START]
   - The removal effect of channel c is the drop in conversion probability:
     Removal_Effect(c) = max(0, P_baseline - P_without_c)

5. Normalization & Attribution Share:
   Each channel's attribution share is its removal effect proportional to the total:
       Share(c) = Removal_Effect(c) / sum_{k} Removal_Effect(k)
   If sum of removal effects is zero (e.g. no effect or degenerate graph),
   shares fall back equally to 1 / M across active channels.

6. Revenue Allocation:
   Attributed Revenue(c) = Share(c) * Total_Conversion_Revenue
   Total Credit = 1.0 (Sum of all shares).
   Total Attributed Revenue = Total Conversion Revenue (Revenue conservation).
"""

from collections import defaultdict, OrderedDict
from typing import Optional
import numpy as np

from backend.app.services.journey_service import CustomerJourney
from .models import AttributionCredit, AttributionResult


START_STATE = "START"
CONVERSION_STATE = "CONVERSION"
NULL_STATE = "NULL"


def calculate_markov_attribution(
    journeys: list[CustomerJourney],
    customer_id: Optional[str] = "aggregate",
) -> AttributionResult:
    """
    Calculate Markov Chain Removal-Effect attribution across a collection of customer journeys.

    Parameters:
        journeys: List of CustomerJourney objects (both converted and non-converted).
        customer_id: Identifier for the output result (defaults to 'aggregate').

    Returns:
        AttributionResult with credits and revenue allocated by Markov removal effect.
    """
    if not journeys:
        return AttributionResult(
            customer_id=customer_id,
            model="markov",
            conversion_revenue=0.0,
            credits=[],
            total_credit=0.0,
        )

    # Filter converted journeys and compute total conversion revenue
    converted_journeys = [
        j for j in journeys
        if j.converted and j.conversion_revenue and j.conversion_revenue > 0
    ]
    total_revenue = sum(float(j.conversion_revenue) for j in converted_journeys)

    if not converted_journeys or total_revenue <= 0:
        return AttributionResult(
            customer_id=customer_id,
            model="markov",
            conversion_revenue=0.0,
            credits=[],
            total_credit=0.0,
        )

    # Collect all unique marketing channels present in converted journeys
    unique_channels: list[str] = []
    for j in converted_journeys:
        for ch in j.channels:
            if ch not in unique_channels:
                unique_channels.append(ch)

    if not unique_channels:
        # Conversions occurred with no recorded marketing touchpoints
        return AttributionResult(
            customer_id=customer_id,
            model="markov",
            conversion_revenue=total_revenue,
            credits=[],
            total_credit=0.0,
        )

    # Fast path: If exactly 1 channel exists across all conversions, it receives 100%
    if len(unique_channels) == 1:
        solo_ch = unique_channels[0]
        return AttributionResult(
            customer_id=customer_id,
            model="markov",
            conversion_revenue=total_revenue,
            credits=[
                AttributionCredit(
                    channel=solo_ch,
                    credit=1.0,
                    attributed_revenue=total_revenue,
                )
            ],
            total_credit=1.0,
        )

    # Step 1: Count state-to-state transitions across all journeys
    transition_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for j in journeys:
        if not j.channels:
            if j.converted:
                transition_counts[START_STATE][CONVERSION_STATE] += 1
            else:
                transition_counts[START_STATE][NULL_STATE] += 1
            continue

        end_state = CONVERSION_STATE if j.converted else NULL_STATE
        path = [START_STATE] + j.channels + [end_state]

        for k in range(len(path) - 1):
            from_st = path[k]
            to_st = path[k + 1]
            transition_counts[from_st][to_st] += 1

    # Step 2: Define transient states: [START] followed by each unique channel
    transient_states = [START_STATE] + unique_channels
    k_dim = len(transient_states)
    state_to_idx = {st: idx for idx, st in enumerate(transient_states)}

    # Step 3: Construct transition probability matrix Q and vector r
    # Q[i, j] = P(transient_i -> transient_j)
    # r[i]    = P(transient_i -> CONVERSION)
    Q = np.zeros((k_dim, k_dim), dtype=float)
    r = np.zeros(k_dim, dtype=float)

    for st, idx in state_to_idx.items():
        out_transitions = transition_counts.get(st, {})
        total_out = sum(out_transitions.values())
        if total_out > 0:
            for next_st, count in out_transitions.items():
                prob = count / total_out
                if next_st in state_to_idx:
                    Q[idx, state_to_idx[next_st]] = prob
                elif next_st == CONVERSION_STATE:
                    r[idx] = prob
                # next_st == NULL_STATE contributes to denominator but has 0 prob to CONVERSION

    # Step 4: Solve for baseline conversion probability from START
    # (I - Q) * x = r  =>  x[0] is P(reach CONVERSION from START)
    I_mat = np.eye(k_dim, dtype=float)
    try:
        x_base = np.linalg.lstsq(I_mat - Q, r, rcond=None)[0]
        p_base = max(0.0, float(x_base[0]))
    except Exception:
        p_base = 0.0

    # Step 5: Calculate removal effect for each channel
    removal_effects: OrderedDict[str, float] = OrderedDict()

    for ch in unique_channels:
        ch_idx = state_to_idx[ch]

        # Clone Q and r and remove transitions out of channel ch
        Q_removed = Q.copy()
        r_removed = r.copy()
        Q_removed[ch_idx, :] = 0.0
        r_removed[ch_idx] = 0.0

        try:
            x_removed = np.linalg.lstsq(I_mat - Q_removed, r_removed, rcond=None)[0]
            p_removed = max(0.0, float(x_removed[0]))
        except Exception:
            p_removed = 0.0

        re = max(0.0, p_base - p_removed)
        removal_effects[ch] = re

    # Step 6: Normalize removal effects into attribution shares
    total_re = sum(removal_effects.values())

    shares: dict[str, float] = {}
    if total_re > 1e-12:
        for ch, re in removal_effects.items():
            shares[ch] = re / total_re
    else:
        # Zero removal effects fallback: equal division among active channels
        equal_share = 1.0 / len(unique_channels)
        for ch in unique_channels:
            shares[ch] = equal_share

    # Step 7: Build AttributionCredit list and verify revenue conservation
    credits: list[AttributionCredit] = []
    for ch in unique_channels:
        credit = shares[ch]
        attributed_rev = credit * total_revenue
        credits.append(
            AttributionCredit(
                channel=ch,
                credit=credit,
                attributed_revenue=attributed_rev,
            )
        )

    total_credit = sum(c.credit for c in credits)

    return AttributionResult(
        customer_id=customer_id,
        model="markov",
        conversion_revenue=total_revenue,
        credits=credits,
        total_credit=total_credit,
    )
