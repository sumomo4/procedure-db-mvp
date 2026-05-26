"""Tests for source document routes."""

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ModuleRowData,
    SourceDocCreateRequest,
    SourceDocDetailData,
    SourceDocListData,
    SourceDocListItemData,
    SourceDocModuleItemData,
    SourceDocUpdateRequest,
)
from app.routers import source_docs


def test_read_source_docs_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document list API should return source document data in the common envelope."""

    def fake_list_source_docs(
        settings: AppSettings,
        keyword: str | None = None,
        status_filter: str | None = None,
    ) -> SourceDocListData:
        """Return deterministic source document list data."""

        assert settings.app_env == "test"
        assert keyword == "M1"
        assert status_filter == "draft"
        return SourceDocListData(
            items=[
                SourceDocListItemData(
                    source_doc_id=1,
                    source_doc_key="BP-STD-001",
                    source_doc_name="M1確認用 原本A",
                    description="確認用の原本です。",
                    source_doc_version_id=10,
                    version_no=1,
                    status="draft",
                    status_label="作成中",
                    module_count=2,
                    enabled_module_count=2,
                    module_names=["初期点検手順", "部品交換手順"],
                    created_by="seed",
                    updated_at="2026-04-22",
                )
            ]
        )

    monkeypatch.setattr(source_docs, "list_source_docs", fake_list_source_docs)

    response = client.get("/api/v1/source-docs?keyword=M1&status=draft")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "items": [
                {
                    "source_doc_id": 1,
                    "source_doc_key": "BP-STD-001",
                    "source_doc_name": "M1確認用 原本A",
                    "description": "確認用の原本です。",
                    "source_doc_version_id": 10,
                    "version_no": 1,
                    "version_major": 0,
                    "version_minor": 0,
                    "version_label": "ver.0.0",
                    "status": "draft",
                    "status_label": "作成中",
                    "module_count": 2,
                    "enabled_module_count": 2,
                    "module_names": ["初期点検手順", "部品交換手順"],
                    "created_by": "seed",
                    "updated_at": "2026-04-22",
                }
            ]
        },
        "message": "原本一覧を取得しました。",
    }


def test_read_source_docs_rejects_invalid_status(client: TestClient) -> None:
    """Source document list API should reject unsupported status values."""

    response = client.get("/api/v1/source-docs?status=invalid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "status must be one of all, draft, review_requested, returned, published, archived.",
    }


def test_read_source_docs_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document list API should return the common error envelope on DB failure."""

    def fake_list_source_docs(
        settings: AppSettings,
        keyword: str | None = None,
        status_filter: str | None = None,
    ) -> SourceDocListData:
        """Raise a deterministic database error."""

        del settings, keyword, status_filter
        raise DatabaseConnectionError("Source document list query failed.")

    monkeypatch.setattr(source_docs, "list_source_docs", fake_list_source_docs)

    response = client.get("/api/v1/source-docs")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Source document list query failed.",
    }


def test_read_source_doc_detail_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document detail API should return linked module data."""

    def fake_get_source_doc_detail(
        settings: AppSettings,
        source_doc_id: int,
    ) -> SourceDocDetailData | None:
        """Return deterministic source document detail data."""

        assert settings.app_env == "test"
        assert source_doc_id == 1
        return SourceDocDetailData(
            source_doc_id=1,
            source_doc_key="BP-STD-001",
            source_doc_name="M1確認用 原本A",
            description="確認用の原本です。",
            source_doc_version_id=10,
            version_no=1,
            status="draft",
            status_label="作成中",
            change_note="Sprint 2 seed",
            module_count=2,
            enabled_module_count=1,
            created_by="seed",
            created_at="2026-04-22",
            updated_at="2026-04-22",
            items=[
                SourceDocModuleItemData(
                    blueprint_item_id=100,
                    item_order=1,
                    enabled=True,
                    module_id=1,
                    module_key="MOD-001",
                    module_name="初期点検手順",
                    module_version_id=11,
                    module_version_no=1,
                    module_status="draft",
                    module_status_label="作成中",
                    rows=[
                        ModuleRowData(
                            module_row_id=1000,
                            row_order=1,
                            row_type="step",
                            major_no="1",
                            middle_no="1",
                            minor_no="1",
                            tech_doc_text="Tech doc",
                            work_text="Check before work.",
                            indent_level=1,
                            expected_result="Ready.",
                            time_text="※",
                            window_text=None,
                            p_text="TT",
                            command_text="show status",
                            note="Tech doc",
                        )
                    ],
                ),
                SourceDocModuleItemData(
                    blueprint_item_id=101,
                    item_order=2,
                    enabled=False,
                    module_id=2,
                    module_key="MOD-002",
                    module_name="部品交換手順",
                    module_version_id=12,
                    module_version_no=1,
                    module_status="published",
                    module_status_label="承認済み",
                    rows=[],
                ),
            ],
        )

    monkeypatch.setattr(source_docs, "get_source_doc_detail", fake_get_source_doc_detail)

    response = client.get("/api/v1/source-docs/1")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "source_doc_id": 1,
            "source_doc_key": "BP-STD-001",
            "source_doc_name": "M1確認用 原本A",
            "description": "確認用の原本です。",
            "source_doc_version_id": 10,
            "version_no": 1,
            "version_major": 0,
            "version_minor": 0,
            "version_label": "ver.0.0",
            "status": "draft",
            "status_label": "作成中",
            "change_note": "Sprint 2 seed",
            "module_count": 2,
            "enabled_module_count": 1,
            "created_by": "seed",
            "created_at": "2026-04-22",
            "updated_at": "2026-04-22",
            "items": [
                {
                    "blueprint_item_id": 100,
                    "item_order": 1,
                    "enabled": True,
                    "module_id": 1,
                    "module_key": "MOD-001",
                    "module_name": "初期点検手順",
                    "module_version_id": 11,
                    "module_version_no": 1,
                    "module_status": "draft",
                    "module_status_label": "作成中",
                    "rows": [
                            {
                                "module_row_id": 1000,
                                "row_order": 1,
                            "row_type": "step",
                            "major_no": "1",
                            "middle_no": "1",
                            "minor_no": "1",
                            "tech_doc_text": "Tech doc",
                            "work_text": "Check before work.",
                            "indent_level": 1,
                            "expected_result": "Ready.",
                            "time_text": "※",
                            "window_text": None,
                                "p_text": "TT",
                                "command_text": "show status",
                                "note": "Tech doc",
                                "device_entries": [],
                                "images": [],
                            }
                        ],
                    },
                {
                    "blueprint_item_id": 101,
                    "item_order": 2,
                    "enabled": False,
                    "module_id": 2,
                    "module_key": "MOD-002",
                    "module_name": "部品交換手順",
                    "module_version_id": 12,
                    "module_version_no": 1,
                    "module_status": "published",
                    "module_status_label": "承認済み",
                    "rows": [],
                },
            ],
        },
        "message": "原本詳細を取得しました。",
    }


def test_read_source_doc_detail_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document detail API should return 404 when data does not exist."""

    def fake_get_source_doc_detail(
        settings: AppSettings,
        source_doc_id: int,
    ) -> SourceDocDetailData | None:
        """Return no source document detail data."""

        del settings, source_doc_id
        return None

    monkeypatch.setattr(source_docs, "get_source_doc_detail", fake_get_source_doc_detail)

    response = client.get("/api/v1/source-docs/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "原本が見つかりませんでした。",
    }


def test_read_source_doc_detail_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document detail API should return the common error envelope on DB failure."""

    def fake_get_source_doc_detail(
        settings: AppSettings,
        source_doc_id: int,
    ) -> SourceDocDetailData | None:
        """Raise a deterministic database error."""

        del settings, source_doc_id
        raise DatabaseConnectionError("Source document detail query failed.")

    monkeypatch.setattr(source_docs, "get_source_doc_detail", fake_get_source_doc_detail)

    response = client.get("/api/v1/source-docs/1")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Source document detail query failed.",
    }


def test_create_source_doc_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document create API should create a source doc and return detail data."""

    def fake_create_source_doc(settings: AppSettings, payload: SourceDocCreateRequest) -> SourceDocDetailData:
        assert settings.app_env == "test"
        assert payload.source_doc_name == "Created source doc"
        assert len(payload.items) == 2
        return SourceDocDetailData(
            source_doc_id=3,
            source_doc_key="BP-STD-003",
            source_doc_name="Created source doc",
            description="Created from API",
            source_doc_version_id=30,
            version_no=1,
            status="draft",
            status_label="菴懈・荳ｭ",
            change_note="Initial draft",
            module_count=2,
            enabled_module_count=1,
            created_by="codex",
            created_at="2026-04-23",
            updated_at="2026-04-23",
            items=[
                SourceDocModuleItemData(
                    blueprint_item_id=300,
                    item_order=1,
                    enabled=True,
                    module_id=1,
                    module_key="MOD-001",
                    module_name="Module A",
                    module_version_id=11,
                    module_version_no=1,
                    module_status="draft",
                    module_status_label="菴懈・荳ｭ",
                    rows=[],
                ),
                SourceDocModuleItemData(
                    blueprint_item_id=301,
                    item_order=2,
                    enabled=False,
                    module_id=2,
                    module_key="MOD-002",
                    module_name="Module B",
                    module_version_id=12,
                    module_version_no=1,
                    module_status="draft",
                    module_status_label="菴懈・荳ｭ",
                    rows=[],
                ),
            ],
        )

    monkeypatch.setattr(source_docs, "create_source_doc", fake_create_source_doc)

    response = client.post(
        "/api/v1/source-docs",
        json={
            "source_doc_name": "Created source doc",
            "description": "Created from API",
            "change_note": "Initial draft",
            "created_by": "codex",
            "items": [
                {"module_id": 1, "enabled": True},
                {"module_id": 2, "enabled": False},
            ],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["result"] == "success"
    assert response.json()["message"] == "原本を作成しました。"
    assert response.json()["data"]["source_doc_key"] == "BP-STD-003"
    assert response.json()["data"]["module_count"] == 2


def test_create_source_doc_rejects_invalid_payload(client: TestClient) -> None:
    """Source document create API should reject invalid request bodies."""

    response = client.post(
        "/api/v1/source-docs",
        json={
            "source_doc_name": "Created source doc",
            "items": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Request validation failed: 1 error(s).",
    }


def test_create_source_doc_rejects_business_validation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document create API should return 400 for business validation errors."""

    def fake_create_source_doc(settings: AppSettings, payload: SourceDocCreateRequest) -> SourceDocDetailData:
        del settings, payload
        raise ValueError("module_id must be unique within items.")

    monkeypatch.setattr(source_docs, "create_source_doc", fake_create_source_doc)

    response = client.post(
        "/api/v1/source-docs",
        json={
            "source_doc_name": "Created source doc",
            "items": [
                {"module_id": 1, "enabled": True},
                {"module_id": 1, "enabled": False},
            ],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "module_id must be unique within items.",
    }


def test_create_source_doc_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document create API should return the common error envelope on DB failure."""

    def fake_create_source_doc(settings: AppSettings, payload: SourceDocCreateRequest) -> SourceDocDetailData:
        del settings, payload
        raise DatabaseConnectionError("Source document create failed.")

    monkeypatch.setattr(source_docs, "create_source_doc", fake_create_source_doc)

    response = client.post(
        "/api/v1/source-docs",
        json={
            "source_doc_name": "Created source doc",
            "items": [{"module_id": 1, "enabled": True}],
        },
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Source document create failed.",
    }


def test_update_source_doc_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document update API should create the next source doc version."""

    def fake_update_source_doc(
        settings: AppSettings,
        source_doc_id: int,
        payload: SourceDocUpdateRequest,
    ) -> SourceDocDetailData | None:
        assert settings.app_env == "test"
        assert source_doc_id == 1
        assert payload.source_doc_name == "Updated source doc"
        assert len(payload.items) == 2
        return SourceDocDetailData(
            source_doc_id=1,
            source_doc_key="BP-STD-001",
            source_doc_name="Updated source doc",
            description="Updated from API",
            source_doc_version_id=31,
            version_no=2,
            status="draft",
            status_label="draft",
            change_note="Second draft",
            module_count=2,
            enabled_module_count=2,
            created_by="codex",
            created_at="2026-04-23",
            updated_at="2026-04-23",
            items=[
                SourceDocModuleItemData(
                    blueprint_item_id=310,
                    item_order=1,
                    enabled=True,
                    module_id=1,
                    module_key="MOD-001",
                    module_name="Module A",
                    module_version_id=11,
                    module_version_no=1,
                    module_status="draft",
                    module_status_label="draft",
                    rows=[],
                ),
                SourceDocModuleItemData(
                    blueprint_item_id=311,
                    item_order=2,
                    enabled=True,
                    module_id=2,
                    module_key="MOD-002",
                    module_name="Module B",
                    module_version_id=12,
                    module_version_no=1,
                    module_status="draft",
                    module_status_label="draft",
                    rows=[],
                ),
            ],
        )

    monkeypatch.setattr(source_docs, "update_source_doc", fake_update_source_doc)

    response = client.put(
        "/api/v1/source-docs/1",
        json={
            "source_doc_name": "Updated source doc",
            "description": "Updated from API",
            "change_note": "Second draft",
            "created_by": "codex",
            "items": [
                {"module_id": 1, "enabled": True},
                {"module_id": 2, "enabled": True},
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"] == "success"
    assert response.json()["message"] == "原本を更新しました。"
    assert response.json()["data"]["source_doc_version_id"] == 31
    assert response.json()["data"]["version_no"] == 2


def test_update_source_doc_rejects_invalid_payload(client: TestClient) -> None:
    """Source document update API should reject invalid request bodies."""

    response = client.put(
        "/api/v1/source-docs/1",
        json={
            "source_doc_name": "Updated source doc",
            "items": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Request validation failed: 1 error(s).",
    }


def test_update_source_doc_rejects_business_validation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document update API should return 400 for business validation errors."""

    def fake_update_source_doc(
        settings: AppSettings,
        source_doc_id: int,
        payload: SourceDocUpdateRequest,
    ) -> SourceDocDetailData | None:
        del settings, source_doc_id, payload
        raise ValueError("module_id must be unique within items.")

    monkeypatch.setattr(source_docs, "update_source_doc", fake_update_source_doc)

    response = client.put(
        "/api/v1/source-docs/1",
        json={
            "source_doc_name": "Updated source doc",
            "items": [
                {"module_id": 1, "enabled": True},
                {"module_id": 1, "enabled": False},
            ],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "module_id must be unique within items.",
    }


def test_update_source_doc_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document update API should return 404 when the source doc does not exist."""

    def fake_update_source_doc(
        settings: AppSettings,
        source_doc_id: int,
        payload: SourceDocUpdateRequest,
    ) -> SourceDocDetailData | None:
        del settings, source_doc_id, payload
        return None

    monkeypatch.setattr(source_docs, "update_source_doc", fake_update_source_doc)

    response = client.put(
        "/api/v1/source-docs/999",
        json={
            "source_doc_name": "Updated source doc",
            "items": [{"module_id": 1, "enabled": True}],
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "原本が見つかりませんでした。",
    }


def test_update_source_doc_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source document update API should return the common error envelope on DB failure."""

    def fake_update_source_doc(
        settings: AppSettings,
        source_doc_id: int,
        payload: SourceDocUpdateRequest,
    ) -> SourceDocDetailData | None:
        del settings, source_doc_id, payload
        raise DatabaseConnectionError("Source document update failed.")

    monkeypatch.setattr(source_docs, "update_source_doc", fake_update_source_doc)

    response = client.put(
        "/api/v1/source-docs/1",
        json={
            "source_doc_name": "Updated source doc",
            "items": [{"module_id": 1, "enabled": True}],
        },
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Source document update failed.",
    }
