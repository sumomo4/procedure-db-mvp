"""Tests for module database access helpers."""

from datetime import datetime, timezone
import sys
from types import ModuleType

import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import ModuleCreateRequest, ModuleCreateRowImageInput, ModuleCreateRowInput, ModuleDetailData, ModuleRowData
from app.db.modules import build_module_diff_data, create_module, get_module_detail, list_module_versions, list_modules


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


def build_diff_module(version_no: int, rows: list[ModuleRowData]) -> ModuleDetailData:
    """Build deterministic module detail data for diff tests."""

    return ModuleDetailData(
        module_id=1,
        module_key="MOD-001",
        module_name="Initial check procedure",
        description="Description",
        module_version_id=version_no,
        version_no=version_no,
        status="draft",
        status_label="Draft",
        row_count=len(rows),
        source_xlsx_path=None,
        created_by="seed",
        header_time_text="09:00",
        target_text="CS",
        common_p_text=">",
        target_device_text="device-01",
        device_headers=[],
        created_at="2026-04-22",
        updated_at="2026-04-22",
        rows=rows,
    )


def build_diff_row(row_id: int, row_order: int, work_text: str | None) -> ModuleRowData:
    """Build deterministic module row data for diff tests."""

    return ModuleRowData(
        module_row_id=row_id,
        row_order=row_order,
        row_type="step",
        major_no=None,
        middle_no=None,
        minor_no=None,
        tech_doc_text=None,
        work_text=work_text,
        indent_level=0,
        expected_result=None,
        time_text=None,
        window_text=None,
        p_text=None,
        command_text=None,
        note=None,
        device_entries=[],
        images=[],
    )


def test_build_module_diff_treats_inserted_blank_as_added() -> None:
    """Diff should avoid marking all later rows as changed when a blank row is inserted."""

    before = build_diff_module(
        1,
        [
            build_diff_row(101, 1, "作業A"),
            build_diff_row(102, 2, "作業B"),
            build_diff_row(103, 3, "作業C"),
        ],
    )
    after = build_diff_module(
        2,
        [
            build_diff_row(201, 1, "作業A"),
            build_diff_row(202, 2, None),
            build_diff_row(203, 3, "作業B"),
            build_diff_row(204, 4, "作業C"),
        ],
    )

    result = build_module_diff_data(before, after)

    assert result.summary.added_count == 1
    assert result.summary.changed_count == 0
    assert result.summary.unchanged_count == 3
    assert [row.status for row in result.rows] == ["unchanged", "added", "unchanged", "unchanged"]


def test_build_module_diff_matches_nearby_similar_rows_as_changed() -> None:
    """Diff should match a nearby edited row using similarity."""

    before = build_diff_module(1, [build_diff_row(101, 1, "TeraTermを起動する")])
    after = build_diff_module(2, [build_diff_row(201, 2, "TeraTermを起動し、接続する")])

    result = build_module_diff_data(before, after)

    assert result.summary.changed_count == 1
    assert result.rows[0].status == "changed"
    assert result.rows[0].changed_fields == ["work_text"]
    assert result.rows[0].similarity is not None


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


def test_list_module_versions_returns_version_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module version query rows should be converted to response data."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            [
                (
                    1,
                    "MOD-001",
                    "Initial check procedure",
                    20,
                    2,
                    "draft",
                    4,
                    "module-v2.xlsm",
                    "webui",
                    datetime(2026, 5, 21, 9, 0, tzinfo=timezone.utc),
                    datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
                ),
                (
                    1,
                    "MOD-001",
                    "Initial check procedure",
                    10,
                    1,
                    "published",
                    3,
                    "module-v1.xlsm",
                    "webui",
                    datetime(2026, 5, 20, 9, 0, tzinfo=timezone.utc),
                    datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc),
                ),
            ]
        ),
    )

    result = list_module_versions(AppSettings(), 1)

    assert fake_cursor.parameters == {"module_id": 1}
    assert result is not None
    assert result.module_id == 1
    assert result.module_key == "MOD-001"
    assert result.items[0].version_no == 2
    assert result.items[0].status_label == "作成中"
    assert result.items[1].status == "published"
    assert result.items[1].updated_at == "2026-05-20"


def test_list_module_versions_returns_none_when_module_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module version query should return none when module does not exist."""

    install_fake_psycopg(monkeypatch, FakeCursor([]))

    assert list_module_versions(AppSettings(), 99) is None


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
                    "09:00",
                    "CS",
                    ">",
                    "device-01",
                    '[{"slot_no": 1, "header_time_text": "09:00", "target_text": "CS", "p_text": ">", "target_device_text": "device-01"}]',
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
                    None,
                    '[{"module_row_image_id": 900, "image_key": "MOD-001_r1_img1", "image_path": "storage/standard/module_images/MOD-001/MOD-001_r1_img1.png", "anchor_cell": "E8", "offset_x_px": 2, "offset_y_px": 3, "width_px": 120, "height_px": 80, "image_order": 1}]',
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
                    "09:00",
                    "CS",
                    ">",
                    "device-01",
                    '[{"slot_no": 1, "header_time_text": "09:00", "target_text": "CS", "p_text": ">", "target_device_text": "device-01"}]',
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
                    None,
                    "[]",
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
    assert result.header_time_text == "09:00"
    assert result.target_text == "CS"
    assert result.common_p_text == ">"
    assert result.target_device_text == "device-01"
    assert result.created_at == "2026-04-22"
    assert result.updated_at == "2026-04-22"
    assert result.rows[0].module_row_id == 100
    assert result.rows[0].major_no == "1"
    assert result.rows[0].tech_doc_text == "Tech doc"
    assert result.rows[0].indent_level == 1
    assert result.rows[0].images[0].image_key == "MOD-001_r1_img1"
    assert result.rows[0].images[0].anchor_cell == "E8"
    assert result.rows[0].images[0].width_px == 120
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
                    "09:00",
                    "CS",
                    ">",
                    "device-01",
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
                    "09:00",
                    "CS",
                    ">",
                    "device-01",
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
        header_time_text="09:00",
        target_text="CS",
        common_p_text=">",
        target_device_text="device-01",
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
                images=[
                    ModuleCreateRowImageInput(
                        image_key="MOD-004_r2_img1",
                        image_path="storage/standard/module_images/MOD-004/MOD-004_r2_img1.png",
                        anchor_cell="E12",
                        offset_x_px=1,
                        offset_y_px=2,
                        width_px=120,
                        height_px=80,
                        image_order=1,
                    )
                ],
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
    assert result.header_time_text == "09:00"
    assert result.target_text == "CS"
    assert result.common_p_text == ">"
    assert result.target_device_text == "device-01"
    assert result.rows[0].row_order == 1
    assert result.rows[1].command_text == "show version"
    executed_queries = "\n".join(query for query, _ in fake_cursor.executions)
    assert "INSERT INTO proc.modules" in executed_queries
    assert "INSERT INTO proc.module_versions" in executed_queries
    assert "INSERT INTO proc.module_rows" in executed_queries
    assert "INSERT INTO proc.module_row_images" in executed_queries


def test_create_module_creates_new_version_for_existing_module_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing module_key should create the next draft version from Excel input."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            rows=[
                (
                    4,
                    "MOD-004",
                    "Updated module",
                    "Updated from Excel",
                    41,
                    2,
                    "draft",
                    "imports/MOD-004-v2.xlsx",
                    "codex",
                    "09:00",
                    "CS",
                    ">",
                    "device-01",
                    '[{"slot_no": 1, "header_time_text": "09:00", "target_text": "CS", "p_text": ">", "target_device_text": "device-01"}]',
                    datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                    datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                    402,
                    1,
                    "step",
                    "1",
                    "1",
                    "1",
                    "Tech doc",
                    "Run updated command",
                    1,
                    "Succeeded",
                    "5分",
                    "console",
                    ">",
                    "show updated version",
                    '[{"slot_no": 1, "time_text": "5分", "window_text": "console", "p_text": ">", "command_text": "show updated version"}]',
                    "[]",
                ),
            ],
            fetchone_results=[
                (4,),
                None,
                (2,),
                (41,),
                (402,),
            ],
        ),
    )

    payload = ModuleCreateRequest(
        module_key="MOD-004",
        module_name="Updated module",
        description="Updated from Excel",
        source_xlsx_path="imports/MOD-004-v2.xlsx",
        created_by="codex",
        header_time_text="09:00",
        target_text="CS",
        common_p_text=">",
        target_device_text="device-01",
        rows=[
            ModuleCreateRowInput(
                row_order=1,
                row_type="step",
                major_no="1",
                middle_no="1",
                minor_no="1",
                tech_doc_text="Tech doc",
                work_text="Run updated command",
                indent_level=1,
                expected_result="Succeeded",
                time_text="5分",
                window_text="console",
                p_text=">",
                command_text="show updated version",
            ),
        ],
    )

    result = create_module(AppSettings(), payload)

    assert result.module_id == 4
    assert result.module_key == "MOD-004"
    assert result.version_no == 2
    assert result.rows[0].work_text == "Run updated command"
    executed_queries = "\n".join(query for query, _ in fake_cursor.executions)
    assert "UPDATE proc.modules" in executed_queries
    assert "INSERT INTO proc.module_versions" in executed_queries
    assert "INSERT INTO proc.modules (module_key" not in executed_queries
    assert any(parameters.get("version_no") == 2 for _, parameters in fake_cursor.executions)


def test_create_module_rejects_existing_module_key_when_draft_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing module_key should be rejected when a draft version already exists."""

    install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            rows=[],
            fetchone_results=[
                (4,),
                (1,),
            ],
        ),
    )
    payload = ModuleCreateRequest(
        module_key="MOD-004",
        module_name="Updated module",
        rows=[
            ModuleCreateRowInput(
                row_order=1,
                row_type="step",
                work_text="Run updated command",
                indent_level=0,
            ),
        ],
    )

    with pytest.raises(ValueError, match="draft module version already exists"):
        create_module(AppSettings(), payload)


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
