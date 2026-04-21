"""Tests for PostgreSQL connectivity helpers."""

import sys
from types import ModuleType

import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.db.connection import check_database_connection


class FakeCursor:
    """Small cursor fake for database connection tests."""

    def __init__(self, query_result: tuple[int] | None) -> None:
        """Store the query result returned by ``fetchone``.

        Args:
            query_result: Result returned by the fake cursor.
        """

        self.query_result = query_result

    def __enter__(self) -> "FakeCursor":
        """Enter the context manager.

        Returns:
            Fake cursor instance.
        """

        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Exit the context manager.

        Args:
            exc_type: Exception type.
            exc_value: Exception value.
            traceback: Traceback object.
        """

    def execute(self, query: str) -> None:
        """Validate the expected health query.

        Args:
            query: SQL query text.

        Raises:
            AssertionError: If an unexpected SQL query is executed.
        """

        assert query == "SELECT 1"

    def fetchone(self) -> tuple[int] | None:
        """Return the configured query result.

        Returns:
            Query result.
        """

        return self.query_result


class FakeConnection:
    """Small connection fake for database connection tests."""

    def __init__(self, query_result: tuple[int] | None) -> None:
        """Store the query result returned by the fake cursor.

        Args:
            query_result: Result returned by the fake cursor.
        """

        self.query_result = query_result

    def __enter__(self) -> "FakeConnection":
        """Enter the context manager.

        Returns:
            Fake connection instance.
        """

        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Exit the context manager.

        Args:
            exc_type: Exception type.
            exc_value: Exception value.
            traceback: Traceback object.
        """

    def cursor(self) -> FakeCursor:
        """Create a fake cursor.

        Returns:
            Fake cursor.
        """

        return FakeCursor(self.query_result)


def install_fake_psycopg(
    monkeypatch: pytest.MonkeyPatch,
    query_result: tuple[int] | None = (1,),
    should_raise: bool = False,
) -> None:
    """Install a fake psycopg module in ``sys.modules``.

    Args:
        monkeypatch: Pytest monkeypatch helper.
        query_result: Result returned by the fake cursor.
        should_raise: Whether the fake connector should raise an exception.
    """

    fake_module = ModuleType("psycopg")

    def connect(database_url: str, connect_timeout: int) -> FakeConnection:
        """Fake psycopg connection factory.

        Args:
            database_url: PostgreSQL connection URL.
            connect_timeout: Connection timeout in seconds.

        Returns:
            Fake connection.

        Raises:
            OSError: If ``should_raise`` is true.
        """

        assert database_url == "postgresql://standard_user:standard_password@localhost:5432/mvp_standard"
        assert connect_timeout == 3
        if should_raise:
            raise OSError("connection refused")
        return FakeConnection(query_result)

    fake_module.connect = connect  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psycopg", fake_module)


def test_check_database_connection_returns_health_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful PostgreSQL check should return database health data."""

    install_fake_psycopg(monkeypatch)

    result = check_database_connection(AppSettings())

    assert result.database == "mvp_standard"
    assert result.host == "localhost"
    assert result.port == 5432
    assert result.status == "ok"


def test_check_database_connection_raises_for_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connection failures should raise DatabaseConnectionError."""

    install_fake_psycopg(monkeypatch, should_raise=True)

    with pytest.raises(DatabaseConnectionError):
        check_database_connection(AppSettings())


def test_check_database_connection_raises_for_invalid_query_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected query results should raise DatabaseConnectionError."""

    install_fake_psycopg(monkeypatch, query_result=None)

    with pytest.raises(DatabaseConnectionError):
        check_database_connection(AppSettings())
