"""Tests for source document routes."""

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    SourceDocDetailData,
    SourceDocListData,
    SourceDocListItemData,
    SourceDocModuleItemData,
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
        "message": "Source documents are available.",
    }


def test_read_source_docs_rejects_invalid_status(client: TestClient) -> None:
    """Source document list API should reject unsupported status values."""

    response = client.get("/api/v1/source-docs?status=invalid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "status must be one of all, draft, published, archived.",
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
                },
            ],
        },
        "message": "Source document detail is available.",
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
        "message": "Source document was not found.",
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
