# -*- coding: utf-8 -*-
"""
backend/scripts/load_data.py

Loads the four CSV files into PostgreSQL using SQLAlchemy Core.

HOW LOADING WORKS
-----------------
We use SQLAlchemy's `text()` to run raw SQL statements, plus pandas
`read_csv()` to read each file into a DataFrame before inserting.

The load strategy is "upsert":
  - INSERT ... ON CONFLICT DO NOTHING

This means:
  - First run:  all rows are inserted.
  - Second run: rows that already exist (same primary/unique key) are silently
    skipped. No duplicates are created.

This is the simplest safe strategy for a development environment. In
production you might use ON CONFLICT DO UPDATE to refresh changed values.

LOAD ORDER
----------
We must respect foreign key constraints:
  1. customers  (no dependencies)
  2. campaigns  (no dependencies)
  3. events     (depends on customers and campaigns)
  4. conversions(depends on customers)

Loading in any other order would violate FK constraints and fail.

BATCH INSERTS
-------------
Instead of inserting one row at a time (slow), we use executemany() with
a list of dicts. SQLAlchemy + psycopg2 sends them in a single round-trip.

ENVIRONMENT
-----------
Reads DATABASE_URL from backend/.env (or the real environment).
Run from the JourneyIQ/ project root.
"""

import sys
from pathlib import Path
from datetime import date

import pandas as pd
from sqlalchemy import create_engine, text

# ─── Path setup ───────────────────────────────────────────────────────────────
# Add backend/ to sys.path so we can import app.config
SCRIPT_DIR   = Path(__file__).resolve().parent   # backend/scripts/
BACKEND_DIR  = SCRIPT_DIR.parent                 # backend/
PROJECT_ROOT = BACKEND_DIR.parent                # JourneyIQ/
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings                  # reads DATABASE_URL from .env

DATA_DIR        = PROJECT_ROOT / "data"
CUSTOMERS_CSV   = DATA_DIR / "customers.csv"
CAMPAIGNS_CSV   = DATA_DIR / "campaigns.csv"
EVENTS_CSV      = DATA_DIR / "customer_events.csv"
CONVERSIONS_CSV = DATA_DIR / "conversions.csv"


# =============================================================================
# Loader functions
# =============================================================================

def load_customers(conn, df: pd.DataFrame) -> int:
    """
    Insert customers. Upsert on customer_id (the business key, UNIQUE column).
    If a customer_id already exists, skip it (DO NOTHING).
    """
    sql = text("""
        INSERT INTO customers (customer_id, first_seen, country, device, customer_segment)
        VALUES (:customer_id, :first_seen, :country, :device, :customer_segment)
        ON CONFLICT (customer_id) DO NOTHING
    """)
    rows = df.to_dict(orient="records")
    result = conn.execute(sql, rows)
    return result.rowcount


def load_campaigns(conn, df: pd.DataFrame) -> int:
    """
    Insert campaigns. Upsert on campaign_id.
    """
    sql = text("""
        INSERT INTO campaigns (campaign_id, name, channel, start_date, end_date, budget, spend)
        VALUES (:campaign_id, :name, :channel, :start_date, :end_date, :budget, :spend)
        ON CONFLICT (campaign_id) DO NOTHING
    """)
    rows = df.to_dict(orient="records")
    result = conn.execute(sql, rows)
    return result.rowcount


def load_events(conn, df: pd.DataFrame) -> int:
    """
    Insert events.

    Events don't have a natural unique key (the same customer could theoretically
    generate the same event at the same millisecond — though extremely unlikely).
    We use a pragmatic approach: check if the events table is empty before loading.

    If not empty, we skip to avoid duplicates on repeated runs.
    This is safe because events are generated deterministically from the same seed.

    WHY NOT ON CONFLICT FOR EVENTS?
    --------------------------------
    The events table has a BIGSERIAL primary key (auto-assigned by the DB).
    The CSV has its own `id` column (1, 2, 3, ...) which differs from what
    PostgreSQL assigns. There is no stable unique business key for events,
    so we protect against duplicates by checking row count instead.
    """
    count_result = conn.execute(text("SELECT COUNT(*) FROM events")).scalar()
    if count_result > 0:
        print(f"      events table already has {count_result:,} rows. Skipping to avoid duplicates.")
        return 0

    # Drop the CSV's `id` column — PostgreSQL will assign its own BIGSERIAL id
    df_clean = df.drop(columns=["id"])

    # Replace NaN with None so SQLAlchemy sends NULL (not the string 'nan')
    df_clean = df_clean.where(pd.notna(df_clean), None)

    sql = text("""
        INSERT INTO events
            (customer_id, timestamp, session_id, channel, campaign_id,
             event_type, page, product_id, device)
        VALUES
            (:customer_id, :timestamp, :session_id, :channel, :campaign_id,
             :event_type, :page, :product_id, :device)
    """)
    rows = df_clean.to_dict(orient="records")
    conn.execute(sql, rows)
    return len(rows)


def load_conversions(conn, df: pd.DataFrame) -> int:
    """
    Insert conversions. Upsert on order_id (UNIQUE constraint in schema).
    """
    sql = text("""
        INSERT INTO conversions (customer_id, timestamp, order_id, product_id, revenue)
        VALUES (:customer_id, :timestamp, :order_id, :product_id, :revenue)
        ON CONFLICT (order_id) DO NOTHING
    """)
    rows = df.to_dict(orient="records")
    result = conn.execute(sql, rows)
    return result.rowcount


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 60)
    print("JourneyIQ -- CSV to PostgreSQL Loader (Stage 2)")
    print("=" * 60)
    print(f"\nDatabase: {settings.DATABASE_URL}\n")

    # ── Check all CSV files exist ────────────────────────────────────────────
    required = [CUSTOMERS_CSV, CAMPAIGNS_CSV, EVENTS_CSV, CONVERSIONS_CSV]
    missing  = [f for f in required if not f.exists()]
    if missing:
        print("ERROR: Missing CSV files:")
        for f in missing:
            print(f"  - {f}")
        print("\nRun: python backend/scripts/generate_data.py")
        sys.exit(1)

    # ── Read CSVs ────────────────────────────────────────────────────────────
    print("[1/5] Reading CSV files ...")
    customers_df   = pd.read_csv(CUSTOMERS_CSV)
    campaigns_df   = pd.read_csv(CAMPAIGNS_CSV)
    events_df      = pd.read_csv(EVENTS_CSV)
    conversions_df = pd.read_csv(CONVERSIONS_CSV)

    print(f"      customers   : {len(customers_df):,} rows")
    print(f"      campaigns   : {len(campaigns_df):,} rows")
    print(f"      events      : {len(events_df):,} rows")
    print(f"      conversions : {len(conversions_df):,} rows")

    # ── Connect to database ──────────────────────────────────────────────────
    print("\n[2/5] Connecting to PostgreSQL ...")
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as test_conn:
            test_conn.execute(text("SELECT 1"))
        print("      [OK] Connection successful")
    except Exception as e:
        print(f"      ERROR: Could not connect to database: {e}")
        print("\n      Make sure:")
        print("      1. PostgreSQL is running")
        print("      2. The database 'journeyiq' exists")
        print("      3. backend/.env has the correct DATABASE_URL")
        sys.exit(1)

    # ── Load in dependency order (customers -> campaigns -> events -> conversions)
    print("\n[3/5] Loading tables ...")
    print("      Order: customers -> campaigns -> events -> conversions")
    print("      (This order respects foreign key constraints)\n")

    with engine.begin() as conn:
        # engine.begin() wraps everything in a transaction.
        # If any insert fails, ALL changes are rolled back automatically.
        # This keeps the database consistent.

        print("      Loading customers ...")
        n_cust = load_customers(conn, customers_df)
        print(f"      Inserted: {n_cust} rows (skipped existing)")

        print("      Loading campaigns ...")
        n_camp = load_campaigns(conn, campaigns_df)
        print(f"      Inserted: {n_camp} rows (skipped existing)")

        print("      Loading events ...")
        n_evt = load_events(conn, events_df)
        print(f"      Inserted: {n_evt} rows")

        print("      Loading conversions ...")
        n_conv = load_conversions(conn, conversions_df)
        print(f"      Inserted: {n_conv} rows (skipped existing)")

    # ── Verify row counts in DB ───────────────────────────────────────────────
    print("\n[4/5] Verifying row counts in database ...")
    with engine.connect() as conn:
        db_counts = {
            "customers":   conn.execute(text("SELECT COUNT(*) FROM customers")).scalar(),
            "campaigns":   conn.execute(text("SELECT COUNT(*) FROM campaigns")).scalar(),
            "events":      conn.execute(text("SELECT COUNT(*) FROM events")).scalar(),
            "conversions": conn.execute(text("SELECT COUNT(*) FROM conversions")).scalar(),
        }

    print(f"      customers   : {db_counts['customers']:,}")
    print(f"      campaigns   : {db_counts['campaigns']:,}")
    print(f"      events      : {db_counts['events']:,}")
    print(f"      conversions : {db_counts['conversions']:,}")

    # Quick sanity
    assert db_counts["customers"]   >= len(customers_df),   "customer count mismatch"
    assert db_counts["campaigns"]   >= len(campaigns_df),   "campaign count mismatch"
    assert db_counts["events"]      >= len(events_df),      "event count mismatch"
    assert db_counts["conversions"] >= len(conversions_df), "conversion count mismatch"

    print("\n[5/5] All checks passed.")
    print("\n" + "=" * 60)
    print("Stage 2 load complete.")
    print("=" * 60)
    print("\nNext: run database/validation.sql in psql to verify data quality.")


if __name__ == "__main__":
    main()
