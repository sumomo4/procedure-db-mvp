"""Tests for source document database access helpers."""

from datetime import datetime, timezone
import sys
from types import ModuleType

import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import SourceDocCreateItemInput, SourceDocCreateRequest, SourceDocUpdateRequest
from app.db.source_docs import (
    cancel_source_doc_registration,
    create_source_doc,
    get_source_doc_detail,
    list_source_docs,
    update_source_doc,
)


class FakeCursor:
    """Small cursor fake for source document query tests."""

    def __init__(
        self,
        rows_per_fetchall: list[list[tuple[object, ...]]] | None = None,
        fetchone_results: list[tuple[object, ...] | None] | None = None,
    ) -> None:
        self.rows_per_fetchall = list(rows_per_fetchall or [[]])
        self.fetchone_results = list(fetchone_results or [])
        self.query = ""
        self.parameters: dict[str, object] = {}
        self.executions: list[tuple[str, dict[str, object]]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, query: str, parameters: dict[str, object]) -> None:
        self.query = query
        self.parameters = parameters
        self.executions.append((query, parameters))

    def fetchone(self) -> tuple[object, ...] | None:
        if not self.fetchone_results:
            return None
        return self.fetchone_results.pop(0)

    def fetchall(self) -> list[tuple[object, ...]]:
        if not self.rows_per_fetchall:
            return []
        return self.rows_per_fetchall.pop(0)


class FakeConnection:
    """Small connection fake for source document query tests."""

    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor
        self.commit_called = False

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return self.fake_cursor

    def commit(self) -> None:
        self.commit_called = True


def install_fake_psycopg(
    monkeypatch: pytest.MonkeyPatch,
    cursor: FakeCursor | None = None,
    should_raise: bool = False,
) -> FakeCursor:
    """Install a fake psycopg module in ``sys.modules``."""

    fake_cursor = cursor or FakeCursor()
    fake_module = ModuleType("psycopg")

    def connect(database_url: str, connect_timeout: int) -> FakeConnection:
        assert database_url == "postgresql://standard_user:standard_password@localhost:5432/mvp_standard"
        assert connect_timeout == 3
        if should_raise:
            raise OSError("connection refused")
        return FakeConnection(fake_cursor)

    fake_module.connect = connect  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psycopg", fake_module)
    return fake_cursor


def test_list_source_docs_returns_source_doc_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Source document query rows should be converted to response data."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            rows_per_fetchall=[
                [
                    (
                        1,
                        "BP-STD-001",
                        "Source doc A",
                        "Description",
                        10,
                        1,
                        0,
                        0,
                        "draft",
                        2,
                        1,
                        ["Module A", "Module B"],
                        "seed",
                        datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc),
                        ["ネットワーク", "SBC"],
                    )
                ],
                [("SBC",), ("ネットワーク",)],
            ]
        ),
    )

    result = list_source_docs(
        AppSettings(),
        keyword="M1",
        status_filter="draft",
        tag_paths=["ネットワーク", "SBC"],
    )

    list_query_parameters = next(
        parameters
        for query, parameters in fake_cursor.executions
        if "b.name AS source_doc_name" in query
    )
    assert list_query_parameters == {
        "keyword": "%M1%",
        "status_filter": "draft",
        "tag_path_0": "ネットワーク",
        "tag_path_1": "SBC",
    }
    assert result.items[0].source_doc_id == 1
    assert result.items[0].source_doc_key == "BP-STD-001"
    assert result.items[0].module_count == 2
    assert result.items[0].tag_paths == ["ネットワーク", "SBC"]
    assert result.tags == ["SBC", "ネットワーク"]
    assert result.items[0].updated_at == "2026-04-22"
    assert any("b.deleted_at IS NULL" in query for query, _ in fake_cursor.executions)
    assert sum("FROM proc.blueprint_tag_memberships tag_filter_" in query for query, _ in fake_cursor.executions) == 1


def test_get_source_doc_detail_returns_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Source document detail rows should be converted to response data."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            rows_per_fetchall=[
                [
                    (
                        1,
                        "BP-STD-001",
                        "Source doc A",
                        "Description",
                        10,
                        1,
                        "draft",
                        "Initial draft",
                        "seed",
                        datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
                        datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc),
                        100,
                        1,
                        True,
                        1,
                        "MOD-001",
                        "Module A",
                        11,
                        1,
                        "draft",
                    )
                ],
                [
                    (
                        100,
                        1000,
                        1,
                        "step",
                        "1",
                        "1",
                        "1",
                        "Tech doc",
                        "Check before work.",
                        1,
                        "Ready.",
                        "5m",
                        "console",
                        ">",
                        "show status",
                        None,
                        '[{"module_row_image_id": 901, "image_key": "BP-STD-001_r1_img1", "image_path": "storage/standard/module_images/MOD-001/BP-STD-001_r1_img1.png", "anchor_cell": "F10", "offset_x_px": 0, "offset_y_px": 1, "width_px": 200, "height_px": 100, "image_order": 1}]',
                    )
                ],
            ]
        ),
    )

    result = get_source_doc_detail(AppSettings(), source_doc_id=1)

    assert any(parameters == {"source_doc_id": "1"} for _, parameters in fake_cursor.executions)
    assert result is not None
    assert result.source_doc_id == 1
    assert result.source_doc_key == "BP-STD-001"
    assert result.module_count == 1
    assert result.items[0].rows[0].command_text == "show status"
    assert result.items[0].rows[0].images[0].anchor_cell == "F10"


def test_create_source_doc_returns_created_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create helper should insert source doc data and return created detail."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            rows_per_fetchall=[
                [
                    (
                        3,
                        "BP-STD-003",
                        "Created source doc",
                        "Created from API",
                        30,
                        1,
                        "draft",
                        "Initial draft",
                        "codex",
                        datetime(2026, 4, 23, 9, 0, tzinfo=timezone.utc),
                        datetime(2026, 4, 23, 9, 0, tzinfo=timezone.utc),
                        300,
                        1,
                        True,
                        1,
                        "MOD-001",
                        "Module A",
                        11,
                        1,
                        "draft",
                    ),
                    (
                        3,
                        "BP-STD-003",
                        "Created source doc",
                        "Created from API",
                        30,
                        1,
                        "draft",
                        "Initial draft",
                        "codex",
                        datetime(2026, 4, 23, 9, 0, tzinfo=timezone.utc),
                        datetime(2026, 4, 23, 9, 0, tzinfo=timezone.utc),
                        301,
                        2,
                        False,
                        2,
                        "MOD-002",
                        "Module B",
                        12,
                        1,
                        "draft",
                    ),
                ],
                [
                    (
                        300,
                        1000,
                        1,
                        "step",
                        "1",
                        "1",
                        "1",
                        "Tech doc",
                        "Check before work.",
                        1,
                        "Ready.",
                        "5m",
                        "console",
                        ">",
                        "show status",
                    ),
                    (
                        301,
                        1001,
                        1,
                        "step",
                        "1",
                        "1",
                        "1",
                        "Tech doc",
                        "Run work.",
                        0,
                        "Done.",
                        None,
                        None,
                        ">",
                        "show version",
                    ),
                ],
            ],
            fetchone_results=[
                (2,),
                (3,),
                (30,),
                (11,),
                (300,),
                (12,),
                (301,),
            ],
        ),
    )

    payload = SourceDocCreateRequest(
        source_doc_name="Created source doc",
        description="Created from API",
        change_note="Initial draft",
        created_by="codex",
        items=[
            SourceDocCreateItemInput(module_id=2, enabled=False, item_order=2),
            SourceDocCreateItemInput(module_id=1, enabled=True, item_order=1),
        ],
    )

    result = create_source_doc(AppSettings(), payload)

    assert result.source_doc_id == 3
    assert result.source_doc_key == "BP-STD-003"
    assert result.module_count == 2
    assert result.enabled_module_count == 1
    assert result.items[0].item_order == 1
    executed_queries = "\n".join(query for query, _ in fake_cursor.executions)
    assert "INSERT INTO proc.blueprints" in executed_queries
    assert "INSERT INTO proc.blueprint_versions" in executed_queries
    assert "INSERT INTO proc.blueprint_items" in executed_queries


def test_create_source_doc_rejects_duplicate_module_id() -> None:
    """Duplicate module_id values should be rejected before DB access."""

    payload = SourceDocCreateRequest(
        source_doc_name="Created source doc",
        items=[
            SourceDocCreateItemInput(module_id=1, enabled=True),
            SourceDocCreateItemInput(module_id=1, enabled=False),
        ],
    )

    with pytest.raises(ValueError, match="module_id must be unique within items."):
        create_source_doc(AppSettings(), payload)


def test_create_source_doc_raises_for_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Create helper should wrap connector failures."""

    install_fake_psycopg(monkeypatch, should_raise=True)
    payload = SourceDocCreateRequest(
        source_doc_name="Created source doc",
        items=[SourceDocCreateItemInput(module_id=1, enabled=True)],
    )

    with pytest.raises(DatabaseConnectionError):
        create_source_doc(AppSettings(), payload)


def test_update_source_doc_returns_updated_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Update helper should create a new source doc version and return detail data."""

    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            rows_per_fetchall=[
                [
                    (
                        1,
                        "BP-STD-001",
                        "Updated source doc",
                        "Updated from API",
                        31,
                        2,
                        "draft",
                        "Second draft",
                        "codex",
                        datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc),
                        datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc),
                        310,
                        1,
                        True,
                        1,
                        "MOD-001",
                        "Module A",
                        11,
                        1,
                        "draft",
                    ),
                    (
                        1,
                        "BP-STD-001",
                        "Updated source doc",
                        "Updated from API",
                        31,
                        2,
                        "draft",
                        "Second draft",
                        "codex",
                        datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc),
                        datetime(2026, 4, 23, 10, 0, tzinfo=timezone.utc),
                        311,
                        2,
                        True,
                        2,
                        "MOD-002",
                        "Module B",
                        12,
                        1,
                        "draft",
                    ),
                ],
                [
                    (
                        310,
                        1000,
                        1,
                        "step",
                        "1",
                        "1",
                        "1",
                        "Tech doc",
                        "Check before work.",
                        1,
                        "Ready.",
                        "5m",
                        "console",
                        ">",
                        "show status",
                    ),
                    (
                        311,
                        1001,
                        1,
                        "step",
                        "1",
                        "1",
                        "1",
                        "Tech doc",
                        "Run work.",
                        0,
                        "Done.",
                        None,
                        None,
                        ">",
                        "show version",
                    ),
                ],
            ],
            fetchone_results=[
                ("BP-STD-001",),
                (2,),
                (0, 0),
                (31,),
                (11,),
                (310,),
                (12,),
                (311,),
            ],
        ),
    )

    payload = SourceDocUpdateRequest(
        source_doc_name="Updated source doc",
        description="Updated from API",
        change_note="Second draft",
        created_by="codex",
        items=[
            SourceDocCreateItemInput(module_id=2, enabled=True, item_order=2),
            SourceDocCreateItemInput(module_id=1, enabled=True, item_order=1),
        ],
    )

    result = update_source_doc(AppSettings(), source_doc_id=1, payload=payload)

    assert result is not None
    assert result.source_doc_id == 1
    assert result.source_doc_version_id == 31
    assert result.version_no == 2
    assert result.module_count == 2
    executed_queries = "\n".join(query for query, _ in fake_cursor.executions)
    assert "UPDATE proc.blueprints" in executed_queries
    assert "INSERT INTO proc.blueprint_versions" in executed_queries
    assert "INSERT INTO proc.blueprint_items" in executed_queries


def test_update_source_doc_returns_none_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Update helper should return None when the source doc does not exist."""

    install_fake_psycopg(
        monkeypatch,
        FakeCursor(fetchone_results=[None]),
    )
    payload = SourceDocUpdateRequest(
        source_doc_name="Updated source doc",
        items=[SourceDocCreateItemInput(module_id=1, enabled=True)],
    )

    result = update_source_doc(AppSettings(), source_doc_id=999, payload=payload)

    assert result is None


def test_update_source_doc_rejects_duplicate_module_id() -> None:
    """Duplicate module_id values should be rejected before DB access."""

    payload = SourceDocUpdateRequest(
        source_doc_name="Updated source doc",
        items=[
            SourceDocCreateItemInput(module_id=1, enabled=True),
            SourceDocCreateItemInput(module_id=1, enabled=False),
        ],
    )

    with pytest.raises(ValueError, match="module_id must be unique within items."):
        update_source_doc(AppSettings(), source_doc_id=1, payload=payload)


def test_update_source_doc_raises_for_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Update helper should wrap connector failures."""

    install_fake_psycopg(monkeypatch, should_raise=True)
    payload = SourceDocUpdateRequest(
        source_doc_name="Updated source doc",
        items=[SourceDocCreateItemInput(module_id=1, enabled=True)],
    )

    with pytest.raises(DatabaseConnectionError):
        update_source_doc(AppSettings(), source_doc_id=1, payload=payload)


def test_cancel_source_doc_registration_marks_initial_unused_draft_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unused initial draft should be logically cancelled with its audit values."""

    cancelled_at = datetime(2026, 9, 10, 10, 30, tzinfo=timezone.utc)
    fake_cursor = install_fake_psycopg(
        monkeypatch,
        FakeCursor(
            fetchone_results=[
                (1, "BP-STD-001", "Source doc A", None, 1, "draft", False),
                (cancelled_at,),
            ]
        ),
    )

    result = cancel_source_doc_registration(
        AppSettings(),
        source_doc_id=1,
        cancelled_by="  Admin User  ",
        reason="  Wrong module composition  ",
        source_doc_key_confirmation="BP-STD-001",
    )

    assert result is not None
    assert result.source_doc_id == 1
    assert result.source_doc_key == "BP-STD-001"
    assert result.cancelled_by == "Admin User"
    assert result.reason == "Wrong module composition"
    assert result.cancelled_at == "2026-09-10T10:30:00+00:00"
    executed_queries = "\n".join(query for query, _ in fake_cursor.executions)
    assert "FROM proc.case_documents" in executed_queries
    assert "UPDATE proc.blueprints" in executed_queries
    assert "delete_reason = %(reason)s" in executed_queries


@pytest.mark.parametrize(
    ("source_doc_row", "message"),
    [
        (
            (1, "BP-STD-001", "Source doc A", None, 2, "draft", False),
            "初版だけが存在する原本のみ登録取消できます。",
        ),
        (
            (1, "BP-STD-001", "Source doc A", None, 1, "published", False),
            "作成中の原本のみ登録取消できます。",
        ),
        (
            (1, "BP-STD-001", "Source doc A", None, 1, "draft", True),
            "案件CSで使用中の原本は登録取消できません。",
        ),
    ],
)
def test_cancel_source_doc_registration_rejects_ineligible_source_doc(
    monkeypatch: pytest.MonkeyPatch,
    source_doc_row: tuple[object, ...],
    message: str,
) -> None:
    """Versioned, approved, and case-used source docs must remain available."""

    install_fake_psycopg(monkeypatch, FakeCursor(fetchone_results=[source_doc_row]))

    with pytest.raises(ValueError, match=message):
        cancel_source_doc_registration(
            AppSettings(),
            source_doc_id=1,
            cancelled_by="Admin User",
            reason="Wrong registration",
            source_doc_key_confirmation="BP-STD-001",
        )


def test_cancel_source_doc_registration_rejects_wrong_key_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact source document key must be supplied before cancellation."""

    install_fake_psycopg(
        monkeypatch,
        FakeCursor(fetchone_results=[(1, "BP-STD-001", "Source doc A", None, 1, "draft", False)]),
    )

    with pytest.raises(ValueError, match="原本IDが一致しません。"):
        cancel_source_doc_registration(
            AppSettings(),
            source_doc_id=1,
            cancelled_by="Admin User",
            reason="Wrong registration",
            source_doc_key_confirmation="BP-STD-999",
        )
