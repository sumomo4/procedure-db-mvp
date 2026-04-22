"""Tests for module database access helpers."""

from datetime import datetime, timezone
import sys
from types import ModuleType

import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.db.modules import list_modules


class FakeCursor:
    """Small cursor fake for module query tests."""

    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        """Store rows returned by ``fetchall``.

        Args:
            rows: Query result rows.
        """

        self.rows = rows
        self.query = ""
        self.parameters: dict[str, str] = {}

    def __enter__(self) -> "FakeCursor":
        """Enter the context manager.

        Returns:
            Fake cursor instance.
        """

        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Exit the context manager."""

    def execute(self, query: str, parameters: dict[str, str]) -> None:
        """Store the executed query and parameters.

        Args:
            query: SQL query text.
            parameters: Query parameters.
        """

        self.query = query
        self.parameters = parameters

    def fetchall(self) -> list[tuple[object, ...]]:
        """Return configured rows.

        Returns:
            Query rows.
        """

        return self.rows


class FakeConnection:
    """Small connection fake for module query tests."""

    def __init__(self, cursor: FakeCursor) -> None:
        """Store cursor returned by ``cursor``.

        Args:
            cursor: Fake cursor.
        """

        self.fake_cursor = cursor

    def __enter__(self) -> "FakeConnection":
        """Enter the context manager.

        Returns:
            Fake connection instance.
        """

        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Exit the context manager."""

    def cursor(self) -> FakeCursor:
        """Return the fake cursor.

        Returns:
            Fake cursor.
        """

        return self.fake_cursor


def install_fake_psycopg(
    monkeypatch: pytest.MonkeyPatch,
    cursor: FakeCursor | None = None,
    should_raise: bool = False,
) -> FakeCursor:
    """Install a fake psycopg module in ``sys.modules``.

    Args:
        monkeypatch: Pytest monkeypatch helper.
        cursor: Optional fake cursor.
        should_raise: Whether the fake connector should raise an exception.

    Returns:
        Fake cursor used by the connection.
    """

    fake_cursor = cursor or FakeCursor([])
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
        return FakeConnection(fake_cursor)

    fake_module.connect = connect  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psycopg", fake_module)
    return fake_cursor


def test_list_modules_returns_module_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module query rows should be converted to response data."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            [
                (
                    1,
                    "MOD-001",
                    "初期点検手順",
                    "説明",
                    10,
                    1,
                    "draft",
                    3,
                    "作業開始前の状態を確認する",
                    None,
                    "seed",
                    datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc),
                )
            ]
        ),
    )

    result = list_modules(AppSettings(), keyword="点検", status_filter="draft")

    assert fake_cursor.parameters == {
        "keyword": "%点検%",
        "status_filter": "draft",
    }
    assert result.items[0].module_id == 1
    assert result.items[0].module_key == "MOD-001"
    assert result.items[0].module_name == "初期点検手順"
    assert result.items[0].status == "draft"
    assert result.items[0].status_label == "作成中"
    assert result.items[0].row_count == 3
    assert result.items[0].updated_at == "2026-04-22"


def test_list_modules_raises_for_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Connection failures should raise DatabaseConnectionError."""

    install_fake_psycopg(monkeypatch, should_raise=True)

    with pytest.raises(DatabaseConnectionError):
        list_modules(AppSettings())
