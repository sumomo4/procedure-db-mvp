"""Database behavior tests for case document bulk execution updates."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

from app.core.config import AppSettings
from app.core.responses import CaseDocExecutionBulkUpdateRequest
from app.db.case_doc_instances import update_case_doc_execution_items


class FakeCursor:
    def __init__(self, selected_rows: list[dict[str, Any]]) -> None:
        self.selected_rows = selected_rows
        self.result: list[dict[str, Any]] = []
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def execute(self, query: str, params: dict[str, Any] | None = None) -> None:
        normalized = " ".join(query.split())
        self.calls.append((normalized, params))
        if normalized.startswith("SELECT execution_item_id, status, lock_version"):
            self.result = self.selected_rows
        elif normalized.startswith("SELECT status, preparation_json"):
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
        elif normalized.startswith("UPDATE proc.case_document_execution_items"):
            self.result = [
                {"execution_item_id": row["execution_item_id"]}
                for row in self.selected_rows
            ]
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


def _payload() -> CaseDocExecutionBulkUpdateRequest:
    return CaseDocExecutionBulkUpdateRequest.model_validate({
        "status": "checked",
        "items": [
            {"execution_item_id": 11, "expected_lock_version": 0},
            {"execution_item_id": 12, "expected_lock_version": 1},
        ],
    })


def test_bulk_update_writes_pending_items_and_histories_atomically(
    test_settings: AppSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = FakeCursor([
        {"execution_item_id": 11, "status": "pending", "lock_version": 0},
        {"execution_item_id": 12, "status": "pending", "lock_version": 1},
    ])
    install_fake_psycopg(monkeypatch, cursor)
    expected_detail = object()
    monkeypatch.setattr(
        "app.db.case_doc_instances.get_case_doc_instance_detail",
        lambda settings, case_document_id: expected_detail,
    )

    result = update_case_doc_execution_items(
        test_settings,
        case_document_id=7,
        payload=_payload(),
        performed_by="実施者A",
    )

    assert result is expected_detail
    update_call = next(call for call in cursor.calls if call[0].startswith("UPDATE proc.case_document_execution_items"))
    assert update_call[1] == {
        "status": "checked",
        "performed_by": "実施者A",
        "skip_reason": None,
        "case_document_id": 7,
        "item_ids": [11, 12],
    }
    assert any(call[0].startswith("INSERT INTO proc.case_document_execution_histories") for call in cursor.calls)


def test_bulk_update_refuses_to_overwrite_completed_items(
    test_settings: AppSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cursor = FakeCursor([
        {"execution_item_id": 11, "status": "checked", "lock_version": 0},
        {"execution_item_id": 12, "status": "pending", "lock_version": 1},
    ])
    install_fake_psycopg(monkeypatch, cursor)

    with pytest.raises(ValueError, match="実施済みの項目"):
        update_case_doc_execution_items(
            test_settings,
            case_document_id=7,
            payload=_payload(),
            performed_by="実施者A",
        )

    assert not any(call[0].startswith("UPDATE proc.case_document_execution_items") for call in cursor.calls)
