"""Tests for case document master repositories."""

from pathlib import Path

from openpyxl import Workbook

from app.core.responses import CaseDocResolveContextRequest
from app.db.case_doc_repositories import ExportFileCaseDocMasterRepository


def _write_workbook(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def _create_access_export_files(export_dir: Path) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    _write_workbook(
        export_dir / "unit_config.xlsx",
        [
            [
                "\u30e6\u30cb\u30c3\u30c8\u69cb\u6210ID",
                "FS\u30af\u30e9\u30b9\u30bf\u540d",
                "\u30d6\u30ed\u30c3\u30af",
                "\u88c5\u7f6e\u8a2d\u7f6e\u90fd\u9053\u5e9c\u770c",
                "\u88c5\u7f6e\u8a2d\u7f6e\u30d3\u30eb",
                "SBC_CL1_0\u7cfb",
                "SBC_CL1_1\u7cfb",
                "GUI_0\u7cfb",
            ],
            [
                "unit-export-001",
                "FS-CL-EXP-01",
                "B900",
                "\u6771\u4eac\u90fd",
                "\u691c\u8a3c\u30d3\u30eb",
                "sbc-exp-cl1-0",
                "sbc-exp-cl1-1",
                "gui-exp-0",
            ],
        ],
    )
    _write_workbook(
        export_dir / "SBC.xlsx",
        [
            ["\u30db\u30b9\u30c8\u540d", "\u30b3\u30de\u30f3\u30c9\u7528\u30d5\u30ed\u30fc\u30c6\u30a3\u30f3\u30b0IP\u30a2\u30c9\u30ec\u30b9"],
            ["sbc-exp-cl1-0", "172.16.1.10"],
            ["sbc-exp-cl1-1", "172.16.1.11"],
        ],
    )
    _write_workbook(
        export_dir / "case_common_values.xlsx",
        [
            ["key", "value", "source_table", "source_column"],
            ["LOGIN_USER", "export-operator", "case_common_values", "login_user"],
        ],
    )


def test_export_file_repository_lists_master_options(tmp_path: Path) -> None:
    """Export file repository should read location options from unit_config.xlsx."""

    _create_access_export_files(tmp_path)
    repository = ExportFileCaseDocMasterRepository(str(tmp_path))

    prefectures = repository.list_prefectures()
    buildings = repository.list_buildings("\u6771\u4eac\u90fd")
    unit_configs = repository.list_unit_configs("\u6771\u4eac\u90fd", "\u691c\u8a3c\u30d3\u30eb")

    assert [item.value for item in prefectures.items] == ["\u6771\u4eac\u90fd"]
    assert [item.value for item in buildings.items] == ["\u691c\u8a3c\u30d3\u30eb"]
    assert unit_configs.items[0].unit_config_id == "unit-export-001"
    assert unit_configs.items[0].fs_cluster_name == "FS-CL-EXP-01"


def test_export_file_repository_resolves_target_sbc_values(tmp_path: Path) -> None:
    """Export file repository should resolve target host and SBC values from xlsx files."""

    _create_access_export_files(tmp_path)
    repository = ExportFileCaseDocMasterRepository(str(tmp_path))

    context = repository.resolve_context(
        CaseDocResolveContextRequest(
            source_doc_id=1,
            prefecture="\u6771\u4eac\u90fd",
            building="\u691c\u8a3c\u30d3\u30eb",
            unit_config_id="unit-export-001",
            target_slot_key="SBC_CL1_1",
        )
    )

    assert context.target_assignment.slot_key == "SBC_CL1_1"
    assert context.target_assignment.host_name == "sbc-exp-cl1-1"
    assert context.common_values[0].value == "export-operator"
    target_ip = next(
        item.value
        for item in context.resolved_placeholders
        if item.placeholder == "SBC_COMMAND_FLOATING_IP" and item.host_name == "sbc-exp-cl1-1"
    )
    assert target_ip == "172.16.1.11"
