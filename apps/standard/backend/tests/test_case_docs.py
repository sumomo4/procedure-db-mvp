"""Tests for case document routes."""

from io import BytesIO

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.core.responses import ModuleRowData, SourceDocDetailData, SourceDocModuleItemData


def _tokyo_prefecture(client: TestClient) -> str:
    response = client.get("/api/v1/case-docs/master/prefectures")
    return response.json()["data"]["items"][0]["value"]


def _tokyo_building(client: TestClient) -> str:
    response = client.get(
        "/api/v1/case-docs/master/buildings",
        params={"prefecture": _tokyo_prefecture(client)},
    )
    return response.json()["data"]["items"][0]["value"]


def _fake_source_doc_detail(source_doc_id: int) -> SourceDocDetailData:
    return SourceDocDetailData(
        source_doc_id=source_doc_id,
        source_doc_key="BP-STD-001",
        source_doc_name="M1\u78ba\u8a8d\u7528 \u539f\u672cA",
        description="test source document",
        source_doc_version_id=10,
        version_no=1,
        status="draft",
        status_label="draft",
        change_note=None,
        module_count=1,
        enabled_module_count=1,
        created_by="pytest",
        created_at="2026-05-12",
        updated_at="2026-05-12",
        items=[
            SourceDocModuleItemData(
                blueprint_item_id=100,
                item_order=1,
                enabled=True,
                module_id=1,
                module_key="MOD-001",
                module_name="01.\u30dc\u30fc\u30ec\u30fc\u30c8\u78ba\u8a8d\u30fb\u4fee\u6b63_CS \u30e2\u30b8\u30e5\u30fc\u30eb1",
                module_version_id=101,
                module_version_no=1,
                module_status="draft",
                module_status_label="draft",
                rows=[
                    ModuleRowData(
                        module_row_id=1000,
                        row_order=1,
                        row_type="work",
                        major_no="0",
                        middle_no="1",
                        minor_no="1",
                        tech_doc_text="",
                        work_text="\u4f5c\u696d\u3067\u4f7f\u7528\u3059\u308bPC\u306eTeraTerm\u8a2d\u5b9a\u3092\u5909\u66f4\u3059\u308b\u3002",
                        indent_level=0,
                        expected_result="\u8a2d\u5b9a\u5909\u66f4\u5b8c\u4e86",
                        time_text=None,
                        window_text=None,
                        p_text=None,
                        command_text="{{SBC_COMMAND_FLOATING_IP}}",
                        note=None,
                    )
                ],
            )
        ],
    )


def _mock_source_doc_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routers.case_docs.get_source_doc_detail",
        lambda settings, source_doc_id: _fake_source_doc_detail(source_doc_id),
    )


def test_read_case_doc_prefectures_returns_options(client: TestClient) -> None:
    """Prefecture master API should return selectable options."""

    response = client.get("/api/v1/case-docs/master/prefectures")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["result"] == "success"
    assert body["data"]["items"]
    assert body["data"]["items"][0]["value"]


def test_read_case_doc_unit_configs_returns_candidates(client: TestClient) -> None:
    """Unit configuration API should filter by selected location."""

    response = client.get(
        "/api/v1/case-docs/master/unit-config",
        params={"prefecture": _tokyo_prefecture(client), "building": _tokyo_building(client)},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["result"] == "success"
    assert body["data"]["items"] == [
        {
            "unit_config_id": "unit-tokyo-001",
            "fs_cluster_name": "FS-CL-TYO-01",
            "block": "B001",
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
        }
    ]


def test_resolve_case_doc_context_returns_no_manual_values(client: TestClient) -> None:
    """Resolve context API should return values derived from master data."""

    response = client.post(
        "/api/v1/case-docs/resolve-context",
        json={
            "source_doc_id": 1,
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
            "unit_config_id": "unit-tokyo-001",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["result"] == "success"
    data = body["data"]
    assert data["unit_config"]["unit_config_id"] == "unit-tokyo-001"
    assert data["target_assignment"]["slot_key"] == "SBC_CL1_0"
    assert data["target_assignment"]["host_name"] == "sbc-tyo-cl1-0"
    assert data["host_assignments"]
    assert data["common_values"] == [
        {
            "key": "LOGIN_USER",
            "value": "cs-operator",
            "source_table": "case_common_values",
            "source_column": "login_user",
            "source": "case_common_values.login_user",
        }
    ]
    assert any(item["placeholder"] == "SBC_COMMAND_FLOATING_IP" for item in data["resolved_placeholders"])
    login_user_placeholder = next(item for item in data["resolved_placeholders"] if item["placeholder"] == "LOGIN_USER")
    assert login_user_placeholder["source_table"] == "case_common_values"
    assert login_user_placeholder["source_column"] == "login_user"


def test_resolve_case_doc_context_rejects_unknown_unit(client: TestClient) -> None:
    """Resolve context API should reject unknown selected master values."""

    response = client.post(
        "/api/v1/case-docs/resolve-context",
        json={
            "source_doc_id": 1,
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
            "unit_config_id": "missing",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["result"] == "error"


def test_resolve_case_doc_context_rejects_non_sbc_target_slot(client: TestClient) -> None:
    """Resolve context API should reject a non-SBC target slot."""

    response = client.post(
        "/api/v1/case-docs/resolve-context",
        json={
            "source_doc_id": 1,
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
            "unit_config_id": "unit-tokyo-001",
            "target_slot_key": "GUI_0",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body["result"] == "error"
    assert body["message"] == "target SBC slot was not found."


def test_generate_case_doc_returns_xlsm_download(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Generate API should return a downloadable workbook package."""

    _mock_source_doc_detail(monkeypatch)

    response = client.post(
        "/api/v1/case-docs/generate",
        json={
            "source_doc_id": 1,
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
            "unit_config_id": "unit-tokyo-001",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/vnd.ms-excel.sheet.macroEnabled.12"
    assert response.headers["content-disposition"] == 'attachment; filename="case-doc-1-unit-tokyo-001.xlsm"'

    workbook = load_workbook(BytesIO(response.content), keep_vba=True)
    assert "01.\u30dc\u30fc\u30ec\u30fc\u30c8\u78ba\u8a8d\u30fb\u4fee\u6b63_CS" in workbook.sheetnames
    assert "\u89e3\u6c7a\u5024" in workbook.sheetnames
    template_sheet = workbook["01.\u30dc\u30fc\u30ec\u30fc\u30c8\u78ba\u8a8d\u30fb\u4fee\u6b63_CS"]
    assert template_sheet["M4"].value == "sbc-tyo-cl1-0"
    assert template_sheet["A6"].value == "0"
    assert template_sheet["B6"].value == "1"
    assert template_sheet["C6"].value == "1"
    assert template_sheet["E6"].value == "\u4f5c\u696d\u3067\u4f7f\u7528\u3059\u308bPC\u306eTeraTerm\u8a2d\u5b9a\u3092\u5909\u66f4\u3059\u308b\u3002"
    assert template_sheet["M6"].value == "10.10.1.10"
    resolved_sheet = workbook["\u89e3\u6c7a\u5024"]
    assert resolved_sheet["A1"].value == "\u6848\u4ef6CS \u751f\u6210\u7d50\u679c"
    assert resolved_sheet["A22"].value == "SBC_COMMAND_FLOATING_IP"
    source_doc_sheet = workbook["\u539f\u672c\u5c55\u958b"]
    assert source_doc_sheet["B2"].value == 1
    assert source_doc_sheet["B3"].value == "BP-STD-001"
    assert source_doc_sheet["I11"].value == "\u4f5c\u696d\u3067\u4f7f\u7528\u3059\u308bPC\u306eTeraTerm\u8a2d\u5b9a\u3092\u5909\u66f4\u3059\u308b\u3002"


def test_resolve_case_doc_context_accepts_target_sbc_slot(client: TestClient) -> None:
    """Resolve context API should use the selected target SBC slot."""

    response = client.post(
        "/api/v1/case-docs/resolve-context",
        json={
            "source_doc_id": 1,
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
            "unit_config_id": "unit-tokyo-001",
            "target_slot_key": "SBC_CL1_1",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()["data"]
    assert data["target_assignment"]["slot_key"] == "SBC_CL1_1"
    assert data["target_assignment"]["host_name"] == "sbc-tyo-cl1-1"


def test_generate_case_doc_uses_selected_target_sbc_slot(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Generate API should place selected target SBC values into the template."""

    _mock_source_doc_detail(monkeypatch)

    response = client.post(
        "/api/v1/case-docs/generate",
        json={
            "source_doc_id": 1,
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
            "unit_config_id": "unit-tokyo-001",
            "target_slot_key": "SBC_CL1_1",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    workbook = load_workbook(BytesIO(response.content), keep_vba=True)
    template_sheet = workbook["01.\u30dc\u30fc\u30ec\u30fc\u30c8\u78ba\u8a8d\u30fb\u4fee\u6b63_CS"]
    assert template_sheet["M4"].value == "sbc-tyo-cl1-1"
    assert template_sheet["M6"].value == "10.10.1.11"
