"""Tests for health check routes."""

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import DatabaseHealthData
from app.routers import health


def test_read_health_returns_success_response(client: TestClient) -> None:
    """Health API should return the common success envelope."""

    response = client.get("/api/v1/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "service": "standard-api-test",
            "environment": "test",
            "status": "ok",
        },
        "message": "API is available.",
    }


def test_read_database_health_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Database health API should return a success envelope when DB check passes."""

    def fake_check_database_connection(settings: AppSettings) -> DatabaseHealthData:
        """Return deterministic database health data.

        Args:
            settings: Application settings.

        Returns:
            Database health data.
        """

        return DatabaseHealthData(
            database=settings.db_name,
            host=settings.db_host,
            port=settings.db_port,
            status="ok",
        )

    monkeypatch.setattr(health, "check_database_connection", fake_check_database_connection)

    response = client.get("/api/v1/health/db")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "database": "mvp_standard_test",
            "host": "test-db",
            "port": 15432,
            "status": "ok",
        },
        "message": "Database connection is available.",
    }


def test_read_database_health_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Database health API should return the common error envelope on DB failure."""

    def fake_check_database_connection(settings: AppSettings) -> DatabaseHealthData:
        """Raise a deterministic database connection error.

        Args:
            settings: Application settings.

        Returns:
            This function does not return normally.

        Raises:
            DatabaseConnectionError: Always raised for this test.
        """

        del settings
        raise DatabaseConnectionError("PostgreSQL connection check failed.")

    monkeypatch.setattr(health, "check_database_connection", fake_check_database_connection)

    response = client.get("/api/v1/health/db")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "PostgreSQL connection check failed.",
    }
