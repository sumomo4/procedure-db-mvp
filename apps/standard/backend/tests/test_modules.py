"""Tests for module routes."""

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ModuleDetailData,
    ModuleDeviceHeaderData,
    ModuleListData,
    ModuleListItemData,
    ModuleRowData,
    ModuleRowDeviceEntryData,
)
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
            header_time_text="09:00",
            target_text="CS",
            common_p_text=">",
            target_device_text="device-01",
            device_headers=[
                ModuleDeviceHeaderData(
                    slot_no=1,
                    header_time_text="09:00",
                    target_text="CS",
                    p_text=">",
                    target_device_text="device-01",
                )
            ],
            created_at="2026-04-22",
            updated_at="2026-04-22",
            rows=[
                ModuleRowData(
                    module_row_id=100,
                    row_order=1,
                    row_type="step",
                    major_no="1",
                    middle_no="1",
                    minor_no="1",
                    tech_doc_text="Tech doc",
                    work_text="Check before work.",
                    indent_level=1,
                    expected_result="Ready.",
                    time_text="□",
                    window_text=None,
                    p_text="TT",
                    command_text="show status",
                    note=None,
                    device_entries=[
                        ModuleRowDeviceEntryData(
                            slot_no=1,
                            time_text="□",
                            window_text=None,
                            p_text="TT",
                            command_text="show status",
                        )
                    ],
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
            "header_time_text": "09:00",
            "target_text": "CS",
            "common_p_text": ">",
            "target_device_text": "device-01",
            "device_headers": [
                {
                    "slot_no": 1,
                    "header_time_text": "09:00",
                    "target_text": "CS",
                    "p_text": ">",
                    "target_device_text": "device-01",
                }
            ],
            "created_at": "2026-04-22",
            "updated_at": "2026-04-22",
            "rows": [
                {
                    "module_row_id": 100,
                    "row_order": 1,
                    "row_type": "step",
                    "major_no": "1",
                    "middle_no": "1",
                    "minor_no": "1",
                    "tech_doc_text": "Tech doc",
                    "work_text": "Check before work.",
                    "indent_level": 1,
                    "expected_result": "Ready.",
                    "time_text": "□",
                    "window_text": None,
                    "p_text": "TT",
                    "command_text": "show status",
                    "note": None,
                    "device_entries": [
                        {
                            "slot_no": 1,
                            "time_text": "□",
                            "window_text": None,
                            "p_text": "TT",
                            "command_text": "show status",
                        }
                    ],
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


def test_create_module_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module create API should create a module and return detail data."""

    def fake_create_module(settings: AppSettings, payload: object) -> ModuleDetailData:
        assert settings.app_env == "test"
        assert payload.module_name == "Created module"
        assert payload.target_text == "CS"
        assert payload.target_device_text == "device-01"
        assert len(payload.rows) == 2
        return ModuleDetailData(
            module_id=4,
            module_key="MOD-004",
            module_name="Created module",
            description="Created from API",
            module_version_id=40,
            version_no=1,
            status="draft",
            status_label="作成中",
            row_count=2,
            source_xlsx_path="imports/MOD-004.xlsx",
            created_by="codex",
            header_time_text="09:00",
            target_text="CS",
            common_p_text=">",
            target_device_text="device-01",
            device_headers=[
                ModuleDeviceHeaderData(
                    slot_no=1,
                    header_time_text="09:00",
                    target_text="CS",
                    p_text=">",
                    target_device_text="device-01",
                )
            ],
            created_at="2026-04-22",
            updated_at="2026-04-22",
            rows=[
                ModuleRowData(
                    module_row_id=400,
                    row_order=1,
                    row_type="header",
                    major_no=None,
                    middle_no=None,
                    minor_no=None,
                    tech_doc_text="Header note",
                    work_text="Preparation",
                    indent_level=0,
                    expected_result=None,
                    time_text=None,
                    window_text=None,
                    p_text=None,
                    command_text=None,
                    note=None,
                    device_entries=[],
                ),
                ModuleRowData(
                    module_row_id=401,
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
                    note=None,
                    device_entries=[
                        ModuleRowDeviceEntryData(
                            slot_no=1,
                            time_text="5分",
                            window_text="console",
                            p_text=">",
                            command_text="show version",
                        )
                    ],
                ),
            ],
        )

    monkeypatch.setattr(modules, "create_module", fake_create_module)

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "description": "Created from API",
            "source_xlsx_path": "imports/MOD-004.xlsx",
            "created_by": "codex",
            "header_time_text": "09:00",
            "target_text": "CS",
            "common_p_text": ">",
            "target_device_text": "device-01",
            "rows": [
                {
                    "row_order": 1,
                    "row_type": "header",
                    "tech_doc_text": "Header note",
                    "work_text": "Preparation",
                    "indent_level": 0,
                },
                {
                    "row_order": 2,
                    "row_type": "step",
                    "major_no": "1",
                    "middle_no": "1",
                    "minor_no": "1",
                    "tech_doc_text": "Tech doc",
                    "work_text": "Run command",
                    "indent_level": 1,
                    "expected_result": "Succeeded",
                    "time_text": "5分",
                    "window_text": "console",
                    "p_text": ">",
                    "command_text": "show version",
                },
            ],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["result"] == "success"
    assert response.json()["message"] == "Module was created."
    assert response.json()["data"]["module_key"] == "MOD-004"
    assert response.json()["data"]["row_count"] == 2


def test_create_module_rejects_invalid_payload(client: TestClient) -> None:
    """Module create API should reject invalid request bodies."""

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "rows": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Request validation failed: 1 error(s).",
    }


def test_create_module_rejects_business_validation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module create API should return 400 for business validation errors."""

    def fake_create_module(settings: AppSettings, payload: object) -> ModuleDetailData:
        del settings, payload
        raise ValueError("row_order must be unique within rows.")

    monkeypatch.setattr(modules, "create_module", fake_create_module)

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "rows": [
                {"row_order": 1, "row_type": "step"},
                {"row_order": 1, "row_type": "step"},
            ],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "row_order must be unique within rows.",
    }


def test_create_module_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module create API should return the common error envelope on DB failure."""

    def fake_create_module(settings: AppSettings, payload: object) -> ModuleDetailData:
        del settings, payload
        raise DatabaseConnectionError("Module create failed.")

    monkeypatch.setattr(modules, "create_module", fake_create_module)

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "rows": [{"row_order": 1, "row_type": "step"}],
        },
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Module create failed.",
    }
