# -*- coding: utf-8 -*-
"""
backend/scripts/generate_data.py

Synthetic data generator for JourneyIQ — Stage 2.

Generates:
  - 500 customers           -> data/customers.csv
  - 15-20 campaigns         -> data/campaigns.csv      (NEW in Stage 2)
  - 3,000-5,000 events      -> data/customer_events.csv
  - ~80 conversions         -> data/conversions.csv    (NEW in Stage 2)

STAGE 2 ADDITIONS
-----------------
1. campaigns.csv is now exported as a proper CSV.
   Campaigns only cover paid channels (Instagram, Facebook, Google Search,
   Google Display, YouTube, Email). Organic Search, Direct, Referral, and SMS
   do NOT have associated campaigns because they are either free/organic or
   direct-response channels where campaign tracking is not applied.

2. Campaign date consistency: when a paid-channel event is generated, the
   generator picks a campaign whose date range covers the event's timestamp.
   This guarantees no event is attributed to a campaign before that campaign
   started or after it ended.

3. Conversion generation:
   - Only customers who reached 'checkout' are eligible to convert.
   - ~35% of customers who checked out actually complete a purchase.
   - The conversion timestamp is 5-30 minutes AFTER their last checkout event
     (payment processing delay).
   - Revenue is drawn from a realistic skewed distribution ($15-$350, median ~$85).
   - order_id is a unique UUID per conversion.
   - product_id matches the product the customer viewed before checkout.

REPRODUCIBILITY
---------------
Random seed 42. Change RANDOM_SEED to get a different dataset.
"""

import uuid
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

# =============================================================================
# Configuration
# =============================================================================

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
fake = Faker()
Faker.seed(RANDOM_SEED)

# --- Output paths ------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent   # backend/scripts/
BACKEND_DIR  = SCRIPT_DIR.parent                 # backend/
PROJECT_ROOT = BACKEND_DIR.parent                # JourneyIQ/
DATA_DIR     = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

CUSTOMERS_CSV   = DATA_DIR / "customers.csv"
CAMPAIGNS_CSV   = DATA_DIR / "campaigns.csv"       # NEW
EVENTS_CSV      = DATA_DIR / "customer_events.csv"
CONVERSIONS_CSV = DATA_DIR / "conversions.csv"     # NEW

# --- Scale -------------------------------------------------------------------
NUM_CUSTOMERS     = 500
NUM_CAMPAIGNS     = 18          # 15-20, settled on 18 for good channel coverage
TARGET_MIN_EVENTS = 3_000
TARGET_MAX_EVENTS = 5_000

# Approx 35% of customers who reach checkout will convert.
CONVERSION_RATE = 0.35

# --- Date window -------------------------------------------------------------
END_DATE   = datetime(2026, 9, 22, tzinfo=timezone.utc)
START_DATE = END_DATE - timedelta(days=180)

# =============================================================================
# Domain constants
# =============================================================================

# All channels (used for events)
CHANNELS = [
    "Instagram",
    "Facebook",
    "Google Search",
    "Google Display",
    "YouTube",
    "Email",
    "SMS",
    "Organic Search",
    "Direct",
    "Referral",
]

CHANNEL_WEIGHTS = [
    0.14,   # Instagram
    0.12,   # Facebook
    0.16,   # Google Search
    0.08,   # Google Display
    0.07,   # YouTube
    0.11,   # Email
    0.05,   # SMS
    0.12,   # Organic Search
    0.09,   # Direct
    0.06,   # Referral
]

# Only paid channels get campaigns.
# SMS is excluded: it is a direct-response channel (we send to our own list;
# there is no external ad platform tracking a "campaign" the way Google/Meta do).
PAID_CHANNELS = [
    "Instagram",
    "Facebook",
    "Google Search",
    "Google Display",
    "YouTube",
    "Email",
]

# Channels where campaign_id is always NULL
NO_CAMPAIGN_CHANNELS = {"Organic Search", "Direct", "Referral", "SMS"}

DEVICES        = ["mobile", "desktop", "tablet"]
DEVICE_WEIGHTS = [0.55, 0.38, 0.07]

COUNTRIES = [
    "United States", "United Kingdom", "Canada", "Australia",
    "Germany", "France", "India", "Brazil", "Mexico", "Spain",
    "Netherlands", "Singapore", "Japan", "Italy", "Sweden",
]
COUNTRY_WEIGHTS = [
    0.30, 0.12, 0.08, 0.07,
    0.06, 0.05, 0.07, 0.04, 0.04, 0.03,
    0.03, 0.02, 0.03, 0.03, 0.03,
]

SEGMENTS        = ["new_visitor", "returning", "loyal", "at_risk", "churned"]
SEGMENT_WEIGHTS = [0.35, 0.30, 0.20, 0.10, 0.05]

PAGES = [
    "/", "/products", "/products/shoes", "/products/bags",
    "/products/accessories", "/blog", "/about", "/sale",
    "/cart", "/checkout", "/search",
]

PRODUCT_IDS = [f"prod_{i:04d}" for i in range(1, 31)]

# --- Funnel ------------------------------------------------------------------
# Events must happen in this order within a session.
FUNNEL_EVENTS = [
    "impression",    # 0 - brand exposure
    "click",         # 1 - user engages
    "page_view",     # 2 - user lands on site
    "product_view",  # 3 - user views product
    "add_to_cart",   # 4 - purchase intent
    "checkout",      # 5 - begins payment (no conversion yet)
]

# Probability of advancing to the NEXT funnel step (real-world drop-off)
FUNNEL_PROGRESS_PROBS = [
    0.65,   # impression  -> click
    0.70,   # click       -> page_view
    0.50,   # page_view   -> product_view
    0.40,   # product_view-> add_to_cart
    0.35,   # add_to_cart -> checkout
]

# =============================================================================
# Helpers
# =============================================================================

def new_uuid() -> str:
    return str(uuid.uuid4())


def weighted_choice(population: list, weights: list):
    return random.choices(population, weights=weights, k=1)[0]


def random_timestamp(after: datetime, max_hours_later: float = 4.0) -> datetime:
    """Return a random timestamp between `after` and `after + max_hours_later`."""
    delta_seconds = random.uniform(30, max_hours_later * 3600)
    return after + timedelta(seconds=delta_seconds)


def random_start_timestamp() -> datetime:
    """Random timestamp anywhere in the 6-month analysis window."""
    span = (END_DATE - START_DATE).total_seconds()
    return START_DATE + timedelta(seconds=random.uniform(0, span))


# =============================================================================
# Step 1 — Generate campaigns
# =============================================================================

def generate_campaigns() -> pd.DataFrame:
    """
    Create NUM_CAMPAIGNS campaign records and return them as a DataFrame.

    Key decisions:
    - Only paid channels get campaigns (PAID_CHANNELS list).
    - Campaign dates are spread across the analysis window but always end
      before END_DATE, so that event timestamps can fall within them.
    - Budget is drawn from a realistic range per channel:
        Social (Instagram/Facebook): $2,000 - $25,000
        Search (Google): $5,000 - $40,000
        Display/Video: $1,500 - $15,000
        Email: $200 - $3,000
    - spend is always <= budget (campaigns don't over-spend).
    - spend_pct is random between 40% and 100% of budget (campaigns are
      partially spent; rarely 100% on the nose).
    """
    # Cycle through paid channels so every channel gets at least 2 campaigns.
    # With 18 campaigns / 6 channels = 3 per channel on average.
    rows = []
    channel_cycle = (PAID_CHANNELS * 4)[:NUM_CAMPAIGNS]  # repeat and truncate
    random.shuffle(channel_cycle)

    budget_ranges = {
        "Instagram":      (2_000,  25_000),
        "Facebook":       (2_000,  25_000),
        "Google Search":  (5_000,  40_000),
        "Google Display": (1_500,  15_000),
        "YouTube":        (1_500,  15_000),
        "Email":          (200,     3_000),
    }

    for i, channel in enumerate(channel_cycle):
        cid        = new_uuid()
        # Campaign starts sometime in the first 4 months of the window
        start_date = START_DATE + timedelta(days=random.randint(0, 120))
        # Runs for 2-8 weeks
        end_date   = start_date + timedelta(days=random.randint(14, 56))
        # Don't let campaigns end beyond our analysis window
        if end_date > END_DATE:
            end_date = END_DATE

        low, high  = budget_ranges[channel]
        budget     = round(random.uniform(low, high), 2)
        spend_pct  = random.uniform(0.40, 1.00)   # 40-100% of budget spent
        spend      = round(budget * spend_pct, 2)

        # Realistic campaign names (brand + channel + quarter/wave)
        wave       = random.choice(["Q1", "Q2", "Spring", "Summer", "Wave A", "Wave B"])
        rows.append({
            "campaign_id": cid,
            "name":        f"JIQ {channel} {wave} {2026}",
            "channel":     channel,
            "start_date":  start_date.date().isoformat(),
            "end_date":    end_date.date().isoformat(),
            "budget":      budget,
            "spend":       spend,
        })

    return pd.DataFrame(rows)


# =============================================================================
# Step 2 — Generate customers
# =============================================================================

def generate_customers() -> pd.DataFrame:
    rows = []
    for _ in range(NUM_CUSTOMERS):
        rows.append({
            "customer_id":      new_uuid(),
            "first_seen":       random_start_timestamp().isoformat(),
            "country":          weighted_choice(COUNTRIES, COUNTRY_WEIGHTS),
            "device":           weighted_choice(DEVICES, DEVICE_WEIGHTS),
            "customer_segment": weighted_choice(SEGMENTS, SEGMENT_WEIGHTS),
        })
    return pd.DataFrame(rows)


# =============================================================================
# Step 3 — Generate events
# =============================================================================

def pick_campaign_for_channel(channel: str, event_ts: datetime,
                               campaigns_df: pd.DataFrame):
    """
    Return a campaign_id that:
      1. Belongs to the given channel (paid only)
      2. Was active at the time of the event (start_date <= event_ts <= end_date)

    Returns None if no matching campaign exists or channel has no campaigns.

    WHY DATE MATCHING?
    ------------------
    Without this check, an event in March could be attributed to a campaign
    that didn't start until June. That would poison attribution analysis.
    We only attribute events to campaigns that were actually running.
    """
    if channel in NO_CAMPAIGN_CHANNELS:
        return None

    # Filter campaigns to same channel that were active on event date
    event_date = event_ts.date()
    mask = (
        (campaigns_df["channel"] == channel) &
        (campaigns_df["start_date"] <= event_date.isoformat()) &
        (campaigns_df["end_date"]   >= event_date.isoformat())
    )
    active = campaigns_df[mask]

    if active.empty:
        # No active campaign for this channel at this time — treat as organic
        return None

    return random.choice(active["campaign_id"].tolist())


def generate_journey_for_customer(customer_id: str, first_seen_str: str,
                                   device: str,
                                   campaigns_df: pd.DataFrame) -> list[dict]:
    """
    Generate a realistic multi-session journey for one customer.

    Returns a list of event dicts, sorted chronologically.
    Each event records the campaign that was active at the time (if any).
    """
    first_seen = datetime.fromisoformat(first_seen_str).replace(tzinfo=timezone.utc)
    events = []

    num_sessions = random.choices(
        [1, 2, 3, 4, 5],
        weights=[0.30, 0.30, 0.22, 0.12, 0.06],
        k=1
    )[0]

    session_start = first_seen

    for session_num in range(num_sessions):
        session_id = new_uuid()
        channel    = weighted_choice(CHANNELS, CHANNEL_WEIGHTS)

        # First session always starts at top of funnel; re-entries start mid-funnel
        funnel_start = 0 if session_num == 0 else random.randint(1, 3)
        current_time = session_start

        for step in range(funnel_start, len(FUNNEL_EVENTS)):
            event_name = FUNNEL_EVENTS[step]

            # Assign campaign at the time of each event (date-consistent)
            campaign_id = pick_campaign_for_channel(channel, current_time, campaigns_df)

            # Determine page and product_id based on event type
            if event_name in ("product_view", "add_to_cart", "checkout"):
                product_id = random.choice(PRODUCT_IDS)
                page       = f"/products/{product_id}"
            elif event_name in ("impression", "click"):
                product_id = None
                page       = None
            else:
                product_id = None
                page       = random.choice(PAGES)

            events.append({
                "customer_id": customer_id,
                "timestamp":   current_time.isoformat(),
                "session_id":  session_id,
                "channel":     channel,
                "campaign_id": campaign_id,
                "event_type":  event_name,
                "page":        page,
                "product_id":  product_id,
                "device":      device,
            })

            # Advance time within the session (30 sec to 10 min per step)
            current_time = random_timestamp(current_time, max_hours_later=0.17)

            # Check for drop-off
            if step < len(FUNNEL_PROGRESS_PROBS):
                if random.random() > FUNNEL_PROGRESS_PROBS[step]:
                    break

        # Gap between sessions: 1-72 hours
        gap_hours = random.uniform(1, 72)
        session_start = current_time + timedelta(hours=gap_hours)

        if session_start > END_DATE:
            break

    return events


def generate_events(customers_df: pd.DataFrame,
                    campaigns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate events for all customers. If volume is below minimum, give
    some customers extra sessions until we reach TARGET_MIN_EVENTS.
    """
    all_events = []

    for _, customer in customers_df.iterrows():
        journey = generate_journey_for_customer(
            customer_id    = customer["customer_id"],
            first_seen_str = customer["first_seen"],
            device         = customer["device"],
            campaigns_df   = campaigns_df,
        )
        all_events.extend(journey)

    # Top-up if needed
    if len(all_events) < TARGET_MIN_EVENTS:
        extra_customers = customers_df.sample(
            n=min(200, len(customers_df)), random_state=RANDOM_SEED
        )
        for _, customer in extra_customers.iterrows():
            if len(all_events) >= TARGET_MIN_EVENTS:
                break
            extra = generate_journey_for_customer(
                customer_id    = customer["customer_id"],
                first_seen_str = customer["first_seen"],
                device         = customer["device"],
                campaigns_df   = campaigns_df,
            )
            all_events.extend(extra)

    events_df = pd.DataFrame(all_events)
    events_df = events_df.sort_values(
        ["customer_id", "timestamp"]
    ).reset_index(drop=True)
    events_df.insert(0, "id", range(1, len(events_df) + 1))
    return events_df


# =============================================================================
# Step 4 — Generate conversions  (NEW in Stage 2)
# =============================================================================

def generate_conversions(customers_df: pd.DataFrame,
                          events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate realistic conversion records.

    LOGIC WALKTHROUGH
    -----------------
    1. Find all customers who had at least one 'checkout' event.
       (Only customers who reached checkout are eligible to buy.)

    2. From that pool, randomly select CONVERSION_RATE (~35%) to actually convert.
       This gives us a realistic conversion rate; not every checkout leads to a
       purchase (payment failures, second thoughts, etc.).

    3. For each converting customer:
       a. Find their LAST checkout event — the purchase happens after that.
       b. Add a payment-processing delay: 5-30 minutes after checkout.
          (This models the time between clicking "Place Order" and confirmation.)
       c. Pick the product_id from their last checkout event so the purchased
          product matches what they were looking at.
       d. Generate revenue using a log-normal distribution, which naturally
          produces the right-skewed shape of real e-commerce orders:
          most orders are $20-$150, occasional orders are $200-$400+.
       e. Assign a unique UUID as the order_id.

    4. Ensure the conversion timestamp is before END_DATE.

    WHAT IS LOG-NORMAL?
    -------------------
    Real e-commerce revenue is right-skewed: most orders are small, but
    there are occasional large orders. Log-normal distribution models this
    perfectly. np.random.lognormal(mean, sigma) where:
      - mean=4.4  -> median order ~$81
      - sigma=0.6 -> spread from ~$30 to ~$350
    """
    # 1. Customers who reached checkout
    checkout_events = events_df[events_df["event_type"] == "checkout"]
    checkout_customers = checkout_events["customer_id"].unique()

    print(f"      Customers who reached checkout: {len(checkout_customers)}")

    # 2. Select converters (~35%)
    num_converters  = max(1, int(len(checkout_customers) * CONVERSION_RATE))
    rng             = np.random.default_rng(RANDOM_SEED + 1)  # separate seed
    converter_ids   = rng.choice(checkout_customers, size=num_converters, replace=False)
    converter_set   = set(converter_ids)

    print(f"      Converting customers (target {CONVERSION_RATE*100:.0f}%): {len(converter_set)}")

    rows = []
    for cid in converter_ids:
        # 3a. Find the last checkout event for this customer
        customer_checkouts = checkout_events[
            checkout_events["customer_id"] == cid
        ].sort_values("timestamp")

        last_checkout = customer_checkouts.iloc[-1]
        checkout_ts   = datetime.fromisoformat(last_checkout["timestamp"]).replace(
            tzinfo=timezone.utc
        )

        # 3b. Payment processing delay: 5-30 minutes after checkout
        delay_minutes = random.uniform(5, 30)
        conv_ts       = checkout_ts + timedelta(minutes=delay_minutes)

        # Don't create conversions beyond the analysis window
        if conv_ts > END_DATE:
            conv_ts = END_DATE - timedelta(minutes=random.uniform(1, 60))

        # 3c. Product — match what the customer was looking at during checkout
        product_id = last_checkout["product_id"]
        if product_id is None or (isinstance(product_id, float) and np.isnan(product_id)):
            product_id = random.choice(PRODUCT_IDS)

        # 3d. Revenue — log-normal, right-skewed, realistic e-commerce values
        revenue = round(float(np.random.lognormal(mean=4.4, sigma=0.6)), 2)
        # Clamp to a sensible range: $10 - $500
        revenue = max(10.00, min(500.00, revenue))

        # 3e. Unique order ID
        order_id = new_uuid()

        rows.append({
            "customer_id": cid,
            "timestamp":   conv_ts.isoformat(),
            "order_id":    order_id,
            "product_id":  product_id,
            "revenue":     revenue,
        })

    conversions_df = pd.DataFrame(rows)
    conversions_df = conversions_df.sort_values("timestamp").reset_index(drop=True)
    return conversions_df


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("JourneyIQ -- Synthetic Data Generator (Stage 2)")
    print("=" * 60)

    # 1. Campaigns
    print(f"\n[1/5] Generating {NUM_CAMPAIGNS} campaigns ...")
    campaigns_df = generate_campaigns()
    print(f"      Channels covered: {sorted(campaigns_df['channel'].unique())}")
    ch_counts = campaigns_df['channel'].value_counts().to_dict()
    print(f"      Per-channel counts: {ch_counts}")
    total_budget = campaigns_df['budget'].sum()
    total_spend  = campaigns_df['spend'].sum()
    print(f"      Total budget: ${total_budget:,.2f}  |  Total spend: ${total_spend:,.2f}")

    # 2. Customers
    print(f"\n[2/5] Generating {NUM_CUSTOMERS} customers ...")
    customers_df = generate_customers()
    print(f"      Countries: {customers_df['country'].nunique()}")
    print(f"      Devices: {customers_df['device'].value_counts().to_dict()}")
    print(f"      Segments: {customers_df['customer_segment'].value_counts().to_dict()}")

    # 3. Events
    print(f"\n[3/5] Generating events ({TARGET_MIN_EVENTS:,}-{TARGET_MAX_EVENTS:,} target) ...")
    events_df    = generate_events(customers_df, campaigns_df)
    total_events = len(events_df)
    print(f"      Total events: {total_events:,}")
    print(f"      Event types:\n{events_df['event_type'].value_counts().to_string()}")
    print(f"\n      Channel distribution:\n{events_df['channel'].value_counts().to_string()}")
    null_campaigns = events_df['campaign_id'].isna().sum()
    print(f"\n      Events with campaign_id=NULL: {null_campaigns:,}  "
          f"(organic/direct channels)")

    # Sanity checks — events
    assert total_events >= TARGET_MIN_EVENTS, \
        f"FAIL: {total_events} events generated, need {TARGET_MIN_EVENTS}"
    assert total_events <= TARGET_MAX_EVENTS + 1000, \
        f"WARN: {total_events} events exceeds target max (minor)"

    merged = events_df.merge(
        customers_df[["customer_id", "first_seen"]], on="customer_id", how="left"
    )
    bad = merged[merged["timestamp"] < merged["first_seen"]]
    assert len(bad) == 0, f"FAIL: {len(bad)} events occur before customer first_seen"
    print(f"\n      [OK] Chronological check: 0 events before first_seen")

    # Sanity check — campaign date consistency
    # (events attributed to a campaign should fall within its date range)
    events_with_camp = events_df[events_df["campaign_id"].notna()].copy()
    events_with_camp = events_with_camp.merge(
        campaigns_df[["campaign_id", "start_date", "end_date"]],
        on="campaign_id", how="left"
    )
    events_with_camp["event_date"] = pd.to_datetime(
        events_with_camp["timestamp"]
    ).dt.date.astype(str)
    out_of_range = events_with_camp[
        (events_with_camp["event_date"] < events_with_camp["start_date"]) |
        (events_with_camp["event_date"] > events_with_camp["end_date"])
    ]
    assert len(out_of_range) == 0, \
        f"FAIL: {len(out_of_range)} events outside their campaign date range"
    print(f"      [OK] Campaign date check: 0 events outside campaign window")

    # 4. Conversions
    print(f"\n[4/5] Generating conversions (target ~{CONVERSION_RATE*100:.0f}% checkout rate) ...")
    conversions_df = generate_conversions(customers_df, events_df)
    print(f"      Total conversions: {len(conversions_df)}")
    print(f"      Revenue stats:")
    print(f"        Min:    ${conversions_df['revenue'].min():.2f}")
    print(f"        Median: ${conversions_df['revenue'].median():.2f}")
    print(f"        Mean:   ${conversions_df['revenue'].mean():.2f}")
    print(f"        Max:    ${conversions_df['revenue'].max():.2f}")
    print(f"        Total:  ${conversions_df['revenue'].sum():,.2f}")

    # Sanity check — conversions should be after checkout
    for _, conv in conversions_df.iterrows():
        cid     = conv["customer_id"]
        conv_ts = conv["timestamp"]
        checkouts = events_df[
            (events_df["customer_id"] == cid) &
            (events_df["event_type"]  == "checkout")
        ]["timestamp"]
        assert checkouts.max() < conv_ts, \
            f"FAIL: conversion for {cid} before last checkout"
    print(f"      [OK] All conversions are after their customer's last checkout")

    # 5. Write CSVs
    print(f"\n[5/5] Writing CSV files to {DATA_DIR} ...")
    customers_df.to_csv(CUSTOMERS_CSV, index=False)
    campaigns_df.to_csv(CAMPAIGNS_CSV, index=False)
    events_df.to_csv(EVENTS_CSV, index=False)
    conversions_df.to_csv(CONVERSIONS_CSV, index=False)

    print(f"      [OK] {CUSTOMERS_CSV.name}    - {len(customers_df):,} rows")
    print(f"      [OK] {CAMPAIGNS_CSV.name}    - {len(campaigns_df):,} rows")
    print(f"      [OK] {EVENTS_CSV.name} - {len(events_df):,} rows")
    print(f"      [OK] {CONVERSIONS_CSV.name} - {len(conversions_df):,} rows")

    print("\n--- campaigns.csv columns ---")
    print(list(campaigns_df.columns))
    print("\n--- conversions.csv columns ---")
    print(list(conversions_df.columns))

    print("\n" + "=" * 60)
    print("Stage 2 data generation complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
