"""Tests for module routes."""

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import ModuleDetailData, ModuleListData, ModuleListItemData, ModuleRowData
from app.routers import modules


def test_read_modules_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module list API should return module data in the common envelope."""

    def fake_list_modules(
        settings: AppSettings,
        keyword: str | None = None,
        status_filter: str | None = None,
    ) -> ModuleListData:
        """Return deterministic module list data."""

        assert settings.app_env == "test"
        assert keyword == "点検"
        assert status_filter == "draft"
        return ModuleListData(
            items=[
                ModuleListItemData(
                    module_id=1,
                    module_key="MOD-001",
                    module_name="初期点検手順",
                    description="説明",
                    module_version_id=10,
                    version_no=1,
                    status="draft",
                    status_label="作成中",
                    row_count=3,
                    first_work_text="作業開始前の状態を確認する",
                    source_xlsx_path=None,
                    created_by="seed",
                    updated_at="2026-04-22",
                )
            ]
        )

    monkeypatch.setattr(modules, "list_modules", fake_list_modules)

    response = client.get("/api/v1/modules?keyword=点検&status=draft")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "items": [
                {
                    "module_id": 1,
                    "module_key": "MOD-001",
                    "module_name": "初期点検手順",
                    "description": "説明",
                    "module_version_id": 10,
                    "version_no": 1,
                    "status": "draft",
                    "status_label": "作成中",
                    "row_count": 3,
                    "first_work_text": "作業開始前の状態を確認する",
                    "source_xlsx_path": None,
                    "created_by": "seed",
                    "updated_at": "2026-04-22",
                }
            ]
        },
        "message": "Modules are available.",
    }


def test_read_modules_rejects_invalid_status(client: TestClient) -> None:
    """Module list API should reject unsupported status values."""

    response = client.get("/api/v1/modules?status=invalid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "status must be one of all, draft, published, archived.",
    }


def test_read_modules_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module list API should return the common error envelope on DB failure."""

    def fake_list_modules(
        settings: AppSettings,
        keyword: str | None = None,
        status_filter: str | None = None,
    ) -> ModuleListData:
        """Raise a deterministic database error."""

        del settings, keyword, status_filter
        raise DatabaseConnectionError("Module list query failed.")

    monkeypatch.setattr(modules, "list_modules", fake_list_modules)

    response = client.get("/api/v1/modules")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Module list query failed.",
    }


def test_read_module_detail_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module detail API should return module data and rows."""

    def fake_get_module_detail(settings: AppSettings, module_id: int) -> ModuleDetailData | None:
        """Return deterministic module detail data."""

        assert settings.app_env == "test"
        assert module_id == 1
        return ModuleDetailData(
            module_id=1,
            module_key="MOD-001",
            module_name="Initial check procedure",
            description="Description",
            module_version_id=10,
            version_no=1,
            status="draft",
            status_label="Draft",
            row_count=1,
            source_xlsx_path=None,
            created_by="seed",
            created_at="2026-04-22",
            updated_at="2026-04-22",
            rows=[
                ModuleRowData(
                    module_row_id=100,
                    row_order=1,
                    row_type="step",
                    work_text="Check before work.",
                    expected_result="Ready.",
                    note=None,
                )
            ],
        )

    monkeypatch.setattr(modules, "get_module_detail", fake_get_module_detail)

    response = client.get("/api/v1/modules/1")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "module_id": 1,
            "module_key": "MOD-001",
            "module_name": "Initial check procedure",
            "description": "Description",
            "module_version_id": 10,
            "version_no": 1,
            "status": "draft",
            "status_label": "Draft",
            "row_count": 1,
            "source_xlsx_path": None,
            "created_by": "seed",
            "created_at": "2026-04-22",
            "updated_at": "2026-04-22",
            "rows": [
                {
                    "module_row_id": 100,
                    "row_order": 1,
                    "row_type": "step",
                    "work_text": "Check before work.",
                    "expected_result": "Ready.",
                    "note": None,
                }
            ],
        },
        "message": "Module detail is available.",
    }


def test_read_module_detail_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module detail API should return 404 when data does not exist."""

    def fake_get_module_detail(settings: AppSettings, module_id: int) -> ModuleDetailData | None:
        """Return no module detail data."""

        del settings, module_id
        return None

    monkeypatch.setattr(modules, "get_module_detail", fake_get_module_detail)

    response = client.get("/api/v1/modules/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Module was not found.",
    }


def test_read_module_detail_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module detail API should return the common error envelope on DB failure."""

    def fake_get_module_detail(settings: AppSettings, module_id: int) -> ModuleDetailData | None:
        """Raise a deterministic database error."""

        del settings, module_id
        raise DatabaseConnectionError("Module detail query failed.")

    monkeypatch.setattr(modules, "get_module_detail", fake_get_module_detail)

    response = client.get("/api/v1/modules/1")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Module detail query failed.",
    }
