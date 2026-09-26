# -*- coding: utf-8 -*-
"""
backend/tests/test_database.py

Unit and integration tests for database configuration and readiness probe:
1. PostgreSQL connection failure must NOT trigger SQLite fallback.
2. Explicit SQLite URL works in development but is forbidden in production.
3. postgres:// scheme is normalized to postgresql://.
4. /api/ready returns 200 only when required tables exist.
5. /api/ready returns 503 when required tables are missing.
6. /api/ready never exposes credentials, connection strings, or stack traces.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from fastapi.testclient import TestClient

from app.database import (
    build_engine,
    check_db_connection,
    check_required_tables,
    check_db_readiness,
    REQUIRED_TABLES,
)
from app.main import app

client = TestClient(app)


class TestDatabaseEngineConfiguration:
    """Tests for database engine creation and fallback prevention."""

    def test_postgres_connection_failure_raises_exception_no_sqlite_fallback(self):
        """
        When PostgreSQL connection fails, build_engine must raise the original
        exception and NEVER fall back to SQLite.
        """
        invalid_url = "postgresql://user:pass@127.0.0.1:54329/nonexistent_db"
        with pytest.raises(OperationalError) as exc_info:
            build_engine(url=invalid_url, environment="production")

        # Verify that an operational error was raised
        assert exc_info.value is not None

    def test_postgres_connection_failure_in_development_also_raises(self):
        """
        Even in development, automatic fallback to SQLite is removed.
        If a PostgreSQL URL is supplied and fails, it must raise.
        """
        invalid_url = "postgresql://user:pass@127.0.0.1:54329/nonexistent_db"
        with pytest.raises(OperationalError):
            build_engine(url=invalid_url, environment="development")

    def test_explicit_sqlite_allowed_in_development(self):
        """Explicit sqlite:/// URL must work in development."""
        sqlite_engine = build_engine(url="sqlite:///:memory:", environment="development")
        try:
            assert sqlite_engine.dialect.name == "sqlite"
        finally:
            sqlite_engine.dispose()

    def test_sqlite_disallowed_in_production(self):
        """SQLite must be strictly disallowed when ENVIRONMENT=production."""
        with pytest.raises(ValueError) as exc_info:
            build_engine(url="sqlite:///:memory:", environment="production")
        assert "production" in str(exc_info.value).lower()
        assert "sqlite" in str(exc_info.value).lower()

    def test_postgres_scheme_normalization(self):
        """Legacy postgres:// scheme must be converted to postgresql://."""
        with patch("app.database.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            # Simulate successful SELECT 1
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn

            build_engine(url="postgres://user:pass@localhost:5432/mydb", environment="development")
            call_url = mock_create_engine.call_args[0][0]
            assert call_url.startswith("postgresql://")
            assert not call_url.startswith("postgres://")


class TestTableVerificationAndReadiness:
    """Tests for table inspection and readiness probe."""

    def test_required_tables_constant(self):
        """Verify the required tables are properly specified."""
        assert REQUIRED_TABLES == {"customers", "campaigns", "events", "conversions"}

    def test_check_required_tables_all_present(self):
        """When all required tables exist, returns (True, [])."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("CREATE TABLE customers (id INT)"))
            conn.execute(text("CREATE TABLE campaigns (id INT)"))
            conn.execute(text("CREATE TABLE events (id INT)"))
            conn.execute(text("CREATE TABLE conversions (id INT)"))
            conn.commit()

        tables_ok, missing = check_required_tables(engine)
        assert tables_ok is True
        assert missing == []
        engine.dispose()

    def test_check_required_tables_missing_some(self):
        """When some required tables are missing, returns (False, missing_list)."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("CREATE TABLE customers (id INT)"))
            conn.execute(text("CREATE TABLE campaigns (id INT)"))
            conn.commit()

        tables_ok, missing = check_required_tables(engine)
        assert tables_ok is False
        assert set(missing) == {"events", "conversions"}
        engine.dispose()

    def test_check_db_readiness_connected_and_ready(self):
        """check_db_readiness returns (True, 'connected') when DB is fully ready."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("CREATE TABLE customers (id INT)"))
            conn.execute(text("CREATE TABLE campaigns (id INT)"))
            conn.execute(text("CREATE TABLE events (id INT)"))
            conn.execute(text("CREATE TABLE conversions (id INT)"))
            conn.commit()

        ready, status = check_db_readiness(engine)
        assert ready is True
        assert status == "connected"
        engine.dispose()

    def test_check_db_readiness_missing_tables(self):
        """check_db_readiness returns (False, 'missing_tables') when tables are absent."""
        engine = create_engine("sqlite:///:memory:")
        ready, status = check_db_readiness(engine)
        assert ready is False
        assert status == "missing_tables"
        engine.dispose()


class TestReadyEndpointAPI:
    """API-level tests for /api/ready endpoint."""

    @patch("app.main.check_required_tables", return_value=(True, []))
    @patch("app.main.check_db_connection", return_value=True)
    def test_ready_200_when_all_tables_present(self, mock_conn, mock_tables):
        res = client.get("/api/ready")
        assert res.status_code == 200
        assert res.json() == {"status": "ready", "database": "connected"}

    @patch("app.main.check_required_tables", return_value=(False, ["events", "conversions"]))
    @patch("app.main.check_db_connection", return_value=True)
    def test_ready_503_when_tables_missing(self, mock_conn, mock_tables):
        res = client.get("/api/ready")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "connected"
        assert "message" in data
        assert "missing" in data["message"].lower()

        # Security check: must not leak database secrets
        assert "postgresql" not in res.text
        assert "sqlite" not in res.text
        assert "password" not in res.text.lower()

    @patch("app.main.check_db_connection", return_value=False)
    def test_ready_503_when_db_disconnected(self, mock_conn):
        res = client.get("/api/ready")
        assert res.status_code == 503
        assert res.json() == {"status": "not_ready", "database": "disconnected"}
        assert "postgresql" not in res.text
        assert "sqlite" not in res.text
