"""Tests for module database access helpers."""

from datetime import datetime, timezone
import sys
from types import ModuleType

import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.db.modules import get_module_detail, list_modules


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


def test_get_module_detail_returns_module_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module detail rows should be converted to response data."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            [
                (
                    1,
                    "MOD-001",
                    "Initial check procedure",
                    "Description",
                    10,
                    1,
                    "draft",
                    None,
                    "seed",
                    datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                    datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc),
                    100,
                    1,
                    "step",
                    "1",
                    "1",
                    "1",
                    "Tech doc",
                    "Check before work.",
                    "Ready.",
                    "□",
                    None,
                    "TT",
                    "show status",
                ),
                (
                    1,
                    "MOD-001",
                    "Initial check procedure",
                    "Description",
                    10,
                    1,
                    "draft",
                    None,
                    "seed",
                    datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                    datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc),
                    101,
                    2,
                    "step",
                    "1",
                    "1",
                    "2",
                    "Tech doc",
                    "Start work.",
                    "Started.",
                    None,
                    None,
                    "TT",
                    "show log",
                ),
            ]
        ),
    )

    result = get_module_detail(AppSettings(), module_id=1)

    assert fake_cursor.parameters == {"module_id": "1"}
    assert result is not None
    assert result.module_id == 1
    assert result.module_key == "MOD-001"
    assert result.status == "draft"
    assert result.status_label == "作成中"
    assert result.row_count == 2
    assert result.created_at == "2026-04-22"
    assert result.updated_at == "2026-04-22"
    assert result.rows[0].module_row_id == 100
    assert result.rows[0].major_no == "1"
    assert result.rows[0].tech_doc_text == "Tech doc"
    assert result.rows[0].time_text == "□"
    assert result.rows[1].command_text == "show log"


def test_get_module_detail_returns_none_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """No query rows should be converted to no detail data."""

    install_fake_psycopg(monkeypatch, FakeCursor([]))

    assert get_module_detail(AppSettings(), module_id=999) is None


def test_get_module_detail_raises_for_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Connection failures should raise DatabaseConnectionError."""

    install_fake_psycopg(monkeypatch, should_raise=True)

    with pytest.raises(DatabaseConnectionError):
        get_module_detail(AppSettings(), module_id=1)
