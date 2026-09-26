"""
backend/app/database.py

SQLAlchemy engine and session factory.

WHY SQLALCHEMY?
---------------
SQLAlchemy gives us two things:
  1. A connection pool (engine) — reuses database connections efficiently
     instead of opening a new TCP connection on every request.
  2. An ORM / Core query builder — lets us write Python instead of raw SQL
     for queries (we'll add ORM models in later stages).

For Stage 1 we only set up the engine and a session factory.
The actual table models will be added in Stage 2.
"""

import os
import logging
import urllib.parse
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_SQLITE_PATH = BACKEND_DIR / "journeyiq.db"
REQUIRED_TABLES = frozenset({"customers", "campaigns", "events", "conversions"})


def seed_sqlite_from_csv(sqlite_path: Path):
    """Seed SQLite database from the project's canonical CSV data files if needed."""
    try:
        import sqlite3
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()

        # Check if customers table already exists and has records
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM customers")
            row = cursor.fetchone()
            if row and row[0] > 0:
                conn.close()
                return

        logger.info("Initializing and seeding SQLite database from CSVs at %s...", DATA_DIR)
        cust_csv = DATA_DIR / "customers.csv"
        camp_csv = DATA_DIR / "campaigns.csv"
        event_csv = DATA_DIR / "customer_events.csv"
        conv_csv = DATA_DIR / "conversions.csv"

        if cust_csv.exists():
            pd.read_csv(cust_csv).to_sql("customers", conn, if_exists="replace", index=False)
        if camp_csv.exists():
            pd.read_csv(camp_csv).to_sql("campaigns", conn, if_exists="replace", index=False)
        if event_csv.exists():
            pd.read_csv(event_csv).to_sql("events", conn, if_exists="replace", index=False)
        if conv_csv.exists():
            pd.read_csv(conv_csv).to_sql("conversions", conn, if_exists="replace", index=False)

        conn.commit()
        conn.close()
        logger.info("Successfully seeded SQLite database with customers, campaigns, events, and conversions.")
    except Exception as e:
        logger.exception("Failed to seed SQLite database: %s", e)


def normalize_database_url(url: str) -> str:
    """
    Normalize DATABASE_URL for SQLAlchemy:
    - Normalizes legacy postgres:// scheme to postgresql://.
    - Safely percent-encodes special characters in user credentials (e.g. '@' in passwords).
    """
    if not url:
        return url
    url = url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url.startswith("sqlite://") or url.startswith("sqlite:"):
        return url

    if "://" in url:
        prefix, rest = url.split("://", 1)
        if "@" in rest:
            last_at = rest.rfind("@")
            creds = rest[:last_at]
            host_part = rest[last_at + 1:]
            if ":" in creds:
                user, password = creds.split(":", 1)
                clean_pw = urllib.parse.quote_plus(urllib.parse.unquote_plus(password))
                url = f"{prefix}://{user}:{clean_pw}@{host_part}"
    return url


def build_engine(url: str | None = None, environment: str | None = None):
    """
    Build SQLAlchemy engine.
    - If DATABASE_URL explicitly starts with sqlite://, allow SQLite only for local development.
    - For PostgreSQL: create engine, test connection with SELECT 1, and raise original exception on failure.
    - Automatic PostgreSQL -> SQLite fallback is strictly disallowed.
    - ENVIRONMENT=production must never use or fall back to SQLite.
    """
    if url is None:
        url = settings.DATABASE_URL
    if environment is None:
        environment = getattr(settings, "ENVIRONMENT", "development")

    if not url:
        raise ValueError("DATABASE_URL is not configured.")

    url = normalize_database_url(url)

    if url.startswith("sqlite://") or url.startswith("sqlite:"):
        if environment == "production":
            raise ValueError(
                "SQLite is not permitted in production environment. "
                "A PostgreSQL DATABASE_URL is required."
            )
        logger.info("Explicit SQLite database configured for local development.")
        seed_sqlite_from_csv(DEFAULT_SQLITE_PATH)
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )

    # For PostgreSQL and other primary databases
    safe_host = url.split("@")[-1] if "@" in url else url
    logger.info("Connecting to primary database (%s)...", safe_host)
    pg_engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        echo=settings.DEBUG,
    )
    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to primary database (%s).", safe_host)
        return pg_engine
    except Exception as e:
        logger.error(
            "Primary database connection failed (%s): %s. "
            "Automatic SQLite fallback is disabled.",
            safe_host,
            e,
        )
        pg_engine.dispose()
        raise


# ─── Engine & Session factory ────────────────────────────────────────────────
engine = build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ─── Base class for ORM models (used in Stage 2+) ─────────────────────────────
# All SQLAlchemy model classes will inherit from Base.
# Defined here so there's one source of truth for the metadata registry.
class Base(DeclarativeBase):
    pass


# ─── Dependency helper (used by FastAPI route functions) ──────────────────────
def get_db():
    """
    FastAPI dependency that yields a database session per request.

    Usage in a route:
        from app.database import get_db
        from sqlalchemy.orm import Session
        from fastapi import Depends

        @app.get("/something")
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # Always close the session, even if an exception occurred.
        # This returns the connection back to the pool.
        db.close()


def check_db_connection(target_engine=None) -> bool:
    """
    Quick connectivity check (SELECT 1).
    Returns True if database is reachable, False otherwise.
    """
    eng = target_engine or engine
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database connection check failed: %s", e)
        return False


def check_required_tables(target_engine=None) -> tuple[bool, list[str]]:
    """
    Verify that all required tables exist in the database:
    customers, campaigns, events, conversions.

    Returns:
        tuple[bool, list[str]]: (True, []) if all required tables exist,
        or (False, [missing_table_names]) if any are missing or if inspection fails.
    """
    eng = target_engine or engine
    try:
        inspector = inspect(eng)
        existing_tables = set(inspector.get_table_names())
        missing = sorted(list(REQUIRED_TABLES - existing_tables))
        if missing:
            logger.warning("Database missing required tables: %s", missing)
            return False, missing
        return True, []
    except Exception as e:
        logger.error("Failed to inspect database tables: %s", e)
        return False, sorted(list(REQUIRED_TABLES))


def check_db_readiness(target_engine=None) -> tuple[bool, str]:
    """
    Comprehensive readiness check verifying both database connectivity (SELECT 1)
    and that all required tables (customers, campaigns, events, conversions) exist.

    Returns:
        tuple[bool, str]:
          - (True, "connected") if reachable and all tables exist.
          - (False, "disconnected") if unreachable.
          - (False, "missing_tables") if connected but required tables are missing.
    """
    eng = target_engine or engine
    if not check_db_connection(eng):
        return False, "disconnected"

    tables_ok, _ = check_required_tables(eng)
    if not tables_ok:
        return False, "missing_tables"

    return True, "connected"
