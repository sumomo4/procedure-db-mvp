"""Database behavior tests for minor-number execution comments."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

from app.core.config import AppSettings
from app.core.responses import CaseDocExecutionCommentUpdateRequest
from app.db.case_doc_instances import update_case_doc_execution_comment


class FakeCursor:
    def __init__(self, existing_lock_version: int | None = None) -> None:
        self.existing_lock_version = existing_lock_version
        self.result: list[dict[str, Any]] = []
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def execute(self, query: str, params: dict[str, Any] | None = None) -> None:
        normalized = " ".join(query.split())
        self.calls.append((normalized, params))
        if normalized.startswith("SELECT status, preparation_json"):
            self.result = [{
                "status": "active",
                "preparation_json": {
                    "construction_name": "東京工事",
                    "construction_date": "2026-09-14",
                    "construction_executor": "実施者A",
                    "block": "B001",
                    "target_fs": "FS-01",
                    "updated_at": "2026-09-14T09:00:00+09:00",
                },
            }]
        elif normalized.startswith("SELECT major_no, middle_no, minor_no"):
            self.result = [{
                "major_no": "0",
                "middle_no": "4",
                "minor_no": "1",
                "first_row_order": 1,
            }]
        elif normalized.startswith("SELECT lock_version"):
            self.result = (
                [{"lock_version": self.existing_lock_version}]
                if self.existing_lock_version is not None
                else []
            )
        elif normalized.startswith("UPDATE proc.case_document_execution_comments"):
            self.result = [{"execution_comment_id": 1}]
        else:
            self.result = []

    def fetchone(self) -> dict[str, Any] | None:
        return self.result[0] if self.result else None

    def fetchall(self) -> list[dict[str, Any]]:
        return self.result


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def cursor(self, **kwargs: object) -> FakeCursor:
        del kwargs
        return self.fake_cursor


def install_fake_psycopg(monkeypatch: pytest.MonkeyPatch, cursor: FakeCursor) -> None:
    psycopg = ModuleType("psycopg")
    psycopg.connect = lambda *args, **kwargs: FakeConnection(cursor)  # type: ignore[attr-defined]
    rows = ModuleType("psycopg.rows")
    rows.dict_row = object()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psycopg", psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", rows)


def test_execution_comment_insert_is_scoped_to_minor_group(
    test_settings: AppSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = FakeCursor()
    install_fake_psycopg(monkeypatch, cursor)
    expected_detail = object()
    monkeypatch.setattr(
        "app.db.case_doc_instances.get_case_doc_instance_detail",
        lambda settings, case_document_id: expected_detail,
    )

    result = update_case_doc_execution_comment(
        test_settings,
        case_document_id=7,
        group_start_row_order=4,
        payload=CaseDocExecutionCommentUpdateRequest(
            comment_text="  想定外の応答を確認  ",
            expected_lock_version=0,
        ),
        updated_by="実施者A",
    )

    assert result is expected_detail
    insert_call = next(
        call for call in cursor.calls
        if call[0].startswith("INSERT INTO proc.case_document_execution_comments")
    )
    assert insert_call[1] is not None
    assert insert_call[1]["case_document_id"] == 7
    assert insert_call[1]["group_start_row_order"] == 4
    assert insert_call[1]["item_label"] == "0.4.1"
    assert insert_call[1]["comment_text"] == "想定外の応答を確認"
    assert insert_call[1]["updated_by"] == "実施者A"


def test_execution_comment_rejects_stale_lock_version(
    test_settings: AppSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = FakeCursor(existing_lock_version=2)
    install_fake_psycopg(monkeypatch, cursor)

    with pytest.raises(ValueError, match="ほかの操作でコメントが更新"):
        update_case_doc_execution_comment(
            test_settings,
            case_document_id=7,
            group_start_row_order=4,
            payload=CaseDocExecutionCommentUpdateRequest(
                comment_text="上書きしない",
                expected_lock_version=1,
            ),
            updated_by="実施者B",
        )

    assert not any(
        call[0].startswith((
            "INSERT INTO proc.case_document_execution_comments",
            "UPDATE proc.case_document_execution_comments",
        ))
        for call in cursor.calls
    )
