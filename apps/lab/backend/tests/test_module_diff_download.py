"""Tests for the module diff workbook download route."""

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import AppSettings
from app.core.responses import (
    ModuleCreateRequest,
    ModuleCreateRowInput,
    ModuleDiffData,
    ModuleDiffSummaryData,
)
from app.routers import modules


def test_download_module_diff_preview_returns_xlsx(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The route should parse the source workbook and return an attachment."""

    imported = ModuleCreateRequest(
        module_name="Imported module",
        rows=[
            ModuleCreateRowInput(
                row_order=1,
                row_type="step",
                work_text="Check system status",
            )
        ],
    )
    diff_data = ModuleDiffData(
        module_id=1,
        module_key="MOD-001",
        module_name="初期点検手順",
        from_version=1,
        to_version=2,
        summary=ModuleDiffSummaryData(
            added_count=0,
            removed_count=0,
            changed_count=1,
            unchanged_count=0,
        ),
        rows=[],
    )

    def fake_import_workbook(**kwargs: object) -> ModuleCreateRequest:
        assert kwargs["workbook_bytes"] == b"source-workbook"
        assert kwargs["filename"] == "module.xlsm"
        return imported

    def fake_get_module_diff_preview(
        settings: AppSettings,
        module_id: int,
        version_no: int,
        payload: object,
    ) -> ModuleDiffData:
        assert settings.app_env == "test"
        assert module_id == 1
        assert version_no == 1
        assert payload is imported
        return diff_data

    def fake_build_module_diff_workbook(
        data: ModuleDiffData,
        workbook_bytes: bytes,
        incoming_payload: ModuleCreateRequest,
    ) -> bytes:
        assert data is diff_data
        assert workbook_bytes == b"source-workbook"
        assert incoming_payload is imported
        return b"generated-xlsx"

    monkeypatch.setattr(
        modules,
        "build_module_create_request_from_workbook_bytes",
        fake_import_workbook,
    )
    monkeypatch.setattr(modules, "get_module_diff_preview", fake_get_module_diff_preview)
    monkeypatch.setattr(
        modules,
        "build_module_diff_workbook",
        fake_build_module_diff_workbook,
    )

    response = client.post(
        "/api/v1/modules/1/diff-preview/download?version_no=1&filename=module.xlsm",
        content=b"source-workbook",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.content == b"generated-xlsx"
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "module-diff-MOD-001-v1-import.xlsx" in response.headers["content-disposition"]
