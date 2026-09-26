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
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_SQLITE_PATH = BACKEND_DIR / "journeyiq.db"


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


def build_engine():
    """Build SQLAlchemy engine with graceful SQLite fallback if primary DB is offline."""
    url = settings.DATABASE_URL

    # Normalize legacy postgres:// scheme provided by some cloud hosts (Render, Heroku)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url.startswith("sqlite"):
        seed_sqlite_from_csv(DEFAULT_SQLITE_PATH)
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )

    # Try connecting to PostgreSQL
    try:
        pg_engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            echo=settings.DEBUG,
        )
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected to primary database: %s", url)
        return pg_engine
    except Exception as e:
        logger.warning(
            "Primary database connection failed (%s). Falling back to local SQLite data store.", e
        )
        seed_sqlite_from_csv(DEFAULT_SQLITE_PATH)
        sqlite_url = f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
        return create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )


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


def check_db_connection() -> bool:
    """
    Quick connectivity check used by the health endpoint.
    Returns True if the database is reachable, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
