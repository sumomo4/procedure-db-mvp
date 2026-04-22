"""Tests for module database access helpers."""

from datetime import datetime, timezone
import sys
from types import ModuleType

import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import ModuleCreateRequest, ModuleCreateRowInput
from app.db.modules import create_module, get_module_detail, list_modules


class FakeCursor:
    """Small cursor fake for module query tests."""

    def __init__(
        self,
        rows: list[tuple[object, ...]],
        fetchone_results: list[tuple[object, ...] | None] | None = None,
    ) -> None:
        """Store rows returned by ``fetchall``.

        Args:
            rows: Query result rows.
        """

        self.rows = rows
        self.query = ""
        self.parameters: dict[str, object] = {}
        self.executions: list[tuple[str, dict[str, object]]] = []
        self.fetchone_results = list(fetchone_results or [])

    def __enter__(self) -> "FakeCursor":
        """Enter the context manager.

        Returns:
            Fake cursor instance.
        """

        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Exit the context manager."""

    def execute(self, query: str, parameters: dict[str, object]) -> None:
        """Store the executed query and parameters.

        Args:
            query: SQL query text.
            parameters: Query parameters.
        """

        self.query = query
        self.parameters = parameters
        self.executions.append((query, parameters))

    def fetchone(self) -> tuple[object, ...] | None:
        """Return the next configured ``fetchone`` result."""

        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

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
        self.commit_called = False

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

    def commit(self) -> None:
        """Record commit calls."""

        self.commit_called = True


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
                    1,
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
                    2,
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
    assert result.rows[0].indent_level == 1
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


def test_create_module_returns_created_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create helper should insert module data and return created detail."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            rows=[
                (
                    4,
                    "MOD-004",
                    "Created module",
                    "Created from API",
                    40,
                    1,
                    "draft",
                    "imports/MOD-004.xlsx",
                    "codex",
                    datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                    datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                    400,
                    1,
                    "header",
                    None,
                    None,
                    None,
                    "Header note",
                    "Preparation",
                    0,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
                (
                    4,
                    "MOD-004",
                    "Created module",
                    "Created from API",
                    40,
                    1,
                    "draft",
                    "imports/MOD-004.xlsx",
                    "codex",
                    datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                    datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                    401,
                    2,
                    "step",
                    "1",
                    "1",
                    "1",
                    "Tech doc",
                    "Run command",
                    1,
                    "Succeeded",
                    "5分",
                    "console",
                    ">",
                    "show version",
                ),
            ],
            fetchone_results=[
                (3,),
                (4, "MOD-004"),
                (40,),
                (400,),
                (401,),
            ],
        ),
    )

    payload = ModuleCreateRequest(
        module_name="Created module",
        description="Created from API",
        source_xlsx_path="imports/MOD-004.xlsx",
        created_by="codex",
        rows=[
            ModuleCreateRowInput(
                row_order=2,
                row_type="step",
                major_no="1",
                middle_no="1",
                minor_no="1",
                tech_doc_text="Tech doc",
                work_text="Run command",
                indent_level=1,
                expected_result="Succeeded",
                time_text="5分",
                window_text="console",
                p_text=">",
                command_text="show version",
            ),
            ModuleCreateRowInput(
                row_order=1,
                row_type="header",
                tech_doc_text="Header note",
                work_text="Preparation",
                indent_level=0,
            ),
        ],
    )

    result = create_module(AppSettings(), payload)

    assert result.module_id == 4
    assert result.module_key == "MOD-004"
    assert result.row_count == 2
    assert result.rows[0].row_order == 1
    assert result.rows[1].command_text == "show version"
    executed_queries = "\n".join(query for query, _ in fake_cursor.executions)
    assert "INSERT INTO proc.modules" in executed_queries
    assert "INSERT INTO proc.module_versions" in executed_queries
    assert "INSERT INTO proc.module_rows" in executed_queries


def test_create_module_rejects_duplicate_row_order() -> None:
    """Duplicate row_order values should be rejected before DB access."""

    payload = ModuleCreateRequest(
        module_name="Created module",
        rows=[
            ModuleCreateRowInput(row_order=1, row_type="step"),
            ModuleCreateRowInput(row_order=1, row_type="step"),
        ],
    )

    with pytest.raises(ValueError, match="row_order must be unique within rows."):
        create_module(AppSettings(), payload)


def test_create_module_raises_for_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create helper should wrap connector failures."""

    install_fake_psycopg(monkeypatch, should_raise=True)
    payload = ModuleCreateRequest(
        module_name="Created module",
        rows=[ModuleCreateRowInput(row_order=1, row_type="step")],
    )

    with pytest.raises(DatabaseConnectionError):
        create_module(AppSettings(), payload)
