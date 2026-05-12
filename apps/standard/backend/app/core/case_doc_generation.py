"""Generate case document workbook bytes from the case document template."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from app.core.responses import CaseDocResolveContextData, SourceDocDetailData


XLSM_MEDIA_TYPE = "application/vnd.ms-excel.sheet.macroEnabled.12"
TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "case_docs" / "case_doc_template.xlsm"
RESOLVED_VALUES_SHEET_NAME = "\u89e3\u6c7a\u5024"
SOURCE_DOC_EXPANSION_SHEET_NAME = "\u539f\u672c\u5c55\u958b"
TEMPLATE_PLACEHOLDER_ALIASES = {
    "DEVICE_NAME": "TARGET_DEVICE_HOSTNAME",
    "NW_ADDRESS": "SBC_COMMAND_FLOATING_IP",
    "USER": "LOGIN_USER",
}


def _u(value: str) -> str:
    """Decode escaped Japanese literals while keeping this source ASCII-safe."""

    try:
        return value.encode("ascii").decode("unicode_escape")
    except UnicodeEncodeError:
        return value


def _clear_sheet(sheet: Worksheet) -> None:
    """Clear cell values from a worksheet while keeping the sheet object."""

    if sheet.max_row > 1:
        sheet.delete_rows(1, sheet.max_row)
    elif sheet.max_row == 1:
        for row in sheet.iter_rows():
            for cell in row:
                cell.value = None


def _write_row(sheet: Worksheet, row_index: int, values: list[object]) -> None:
    for column_index, value in enumerate(values, start=1):
        sheet.cell(row=row_index, column=column_index, value=value)


def _style_heading(sheet: Worksheet, row_index: int) -> None:
    fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    for cell in sheet[row_index]:
        cell.font = Font(bold=True)
        cell.fill = fill


def _value_for_target_host(context: CaseDocResolveContextData, placeholder: str) -> str | None:
    """Return a resolved placeholder value tied to the selected target host name."""

    target_host_name = context.target_assignment.host_name
    return next(
        (
            item.value
            for item in context.resolved_placeholders
            if item.placeholder == placeholder and item.host_name == target_host_name
        ),
        None,
    )


def _add_legacy_placeholder_aliases(values: dict[str, str]) -> None:
    for legacy_name, formal_name in TEMPLATE_PLACEHOLDER_ALIASES.items():
        if formal_name in values:
            values.setdefault(legacy_name, values[formal_name])


def _build_placeholder_values(context: CaseDocResolveContextData) -> dict[str, str]:
    """Build template values after the target host name has been resolved."""

    values = {item.key: item.value for item in context.common_values}
    values["TARGET_DEVICE_HOSTNAME"] = context.target_assignment.host_name

    target_command_floating_ip = _value_for_target_host(context, "SBC_COMMAND_FLOATING_IP")
    if target_command_floating_ip:
        values["SBC_COMMAND_FLOATING_IP"] = target_command_floating_ip

    for item in context.resolved_placeholders:
        values.setdefault(item.placeholder, item.value)

    _add_legacy_placeholder_aliases(values)
    return values


def _replace_placeholders(sheet: Worksheet, values: dict[str, str]) -> None:
    """Replace {{PLACEHOLDER}} strings in one template worksheet."""

    for row in sheet.iter_rows():
        for cell in row:
            if not isinstance(cell.value, str) or "{{" not in cell.value:
                continue
            replaced = cell.value
            for key, value in values.items():
                replaced = replaced.replace(f"{{{{{key}}}}}", value)
            cell.value = replaced


def _write_resolved_values_sheet(sheet: Worksheet, context: CaseDocResolveContextData) -> None:
    """Write resolved values to an auditable worksheet in the template copy."""

    host_assignment_title = _u("\\u30db\\u30b9\\u30c8\\u5272\\u5f53")
    common_value_title = _u("\\u5171\\u901a\\u5024")
    resolved_value_title = _u("\\u89e3\\u6c7a\\u6e08\\u307f\\u5024")
    host_header = [_u("\\u30b9\\u30ed\\u30c3\\u30c8"), _u("\\u88c5\\u7f6e\\u7a2e\\u5225"), _u("\\u7cfb"), _u("\\u30db\\u30b9\\u30c8\\u540d")]
    common_header = [_u("\\u30ad\\u30fc"), _u("\\u5024"), _u("\\u51fa\\u5178")]
    resolved_header = [_u("\\u5024\\u540d"), _u("\\u5024"), _u("\\u51fa\\u5178\\u30c6\\u30fc\\u30d6\\u30eb"), _u("\\u51fa\\u5178\\u30ab\\u30e9\\u30e0"), _u("\\u30db\\u30b9\\u30c8\\u540d")]

    _clear_sheet(sheet)
    rows: list[list[object]] = [
        [_u("\\u6848\\u4ef6CS \\u751f\\u6210\\u7d50\\u679c")],
        [_u("\\u539f\\u672cID"), context.source_doc_id],
        [_u("\\u30e6\\u30cb\\u30c3\\u30c8\\u69cb\\u6210ID"), context.unit_config.unit_config_id],
        [_u("FS\\u30af\\u30e9\\u30b9\\u30bf"), context.unit_config.fs_cluster_name],
        [_u("\\u30d6\\u30ed\\u30c3\\u30af"), context.unit_config.block],
        [_u("\\u90fd\\u9053\\u5e9c\\u770c"), context.unit_config.prefecture],
        [_u("\\u30d3\\u30eb"), context.unit_config.building],
        [],
        [host_assignment_title],
        host_header,
    ]
    rows.extend(
        [assignment.slot_key, assignment.device_type, assignment.system or "-", assignment.host_name]
        for assignment in context.host_assignments
    )
    rows.extend(
        [
            [],
            [common_value_title],
            common_header,
        ]
    )
    rows.extend([item.key, item.value, item.source] for item in context.common_values)
    rows.extend(
        [
            [],
            [resolved_value_title],
            resolved_header,
        ]
    )
    rows.extend(
        [item.placeholder, item.value, item.source_table, item.source_column, item.host_name or "-"]
        for item in context.resolved_placeholders
    )

    for row_index, values in enumerate(rows, start=1):
        _write_row(sheet, row_index, values)
        if values and len(values) == 1:
            sheet.cell(row=row_index, column=1).font = Font(bold=True, size=14)
        if values in (host_header, common_header, resolved_header):
            _style_heading(sheet, row_index)

    for column_letter, width in {"A": 24, "B": 28, "C": 22, "D": 24, "E": 24}.items():
        sheet.column_dimensions[column_letter].width = width
    sheet.freeze_panes = "A10"


def _write_source_doc_expansion_sheet(sheet: Worksheet, source_doc: SourceDocDetailData) -> None:
    """Write source document modules and rows used by the generated case document."""

    source_doc_title = _u("\u539f\u672c\u5c55\u958b")
    enabled_text = _u("\u6709\u52b9")
    disabled_text = _u("\u7121\u52b9")
    row_header = [
        _u("\u30e2\u30b8\u30e5\u30fc\u30eb\u9806"),
        _u("\u6709\u52b9\u72b6\u614b"),
        _u("\u30e2\u30b8\u30e5\u30fc\u30ebID"),
        _u("\u30e2\u30b8\u30e5\u30fc\u30eb\u540d"),
        _u("\u884c\u9806"),
        _u("\u5927"),
        _u("\u4e2d"),
        _u("\u5c0f"),
        _u("\u4f5c\u696d\u5185\u5bb9"),
        _u("\u78ba\u8a8d\u7d50\u679c"),
        _u("\u30b3\u30de\u30f3\u30c9"),
    ]

    _clear_sheet(sheet)
    rows: list[list[object]] = [
        [source_doc_title],
        [_u("\u539f\u672cID"), source_doc.source_doc_id],
        [_u("\u539f\u672c\u30ad\u30fc"), source_doc.source_doc_key],
        [_u("\u539f\u672c\u540d"), source_doc.source_doc_name],
        [_u("\u7248"), source_doc.version_no],
        [_u("\u30e2\u30b8\u30e5\u30fc\u30eb\u6570"), source_doc.module_count],
        [_u("\u6709\u52b9\u30e2\u30b8\u30e5\u30fc\u30eb\u6570"), source_doc.enabled_module_count],
        [],
        [
            _u("\u203b\u6848\u4ef6CS\u751f\u6210\u3067\u306f\u3001\u539f\u672c\u306b\u7d10\u3065\u304f\u6709\u52b9\u30e2\u30b8\u30e5\u30fc\u30eb\u3092\u9806\u756a\u3069\u304a\u308a\u5c55\u958b\u3057\u307e\u3059\u3002")
        ],
        row_header,
    ]

    for module in sorted(source_doc.items, key=lambda item: item.item_order):
        module_status = enabled_text if module.enabled else disabled_text
        if not module.enabled:
            rows.append(
                [
                    module.item_order,
                    module_status,
                    module.module_key,
                    module.module_name,
                    "-",
                    "-",
                    "-",
                    "-",
                    _u("\u6848\u4ef6CS\u751f\u6210\u5bfe\u8c61\u5916"),
                    "-",
                    "-",
                ]
            )
            continue

        if not module.rows:
            rows.append(
                [
                    module.item_order,
                    module_status,
                    module.module_key,
                    module.module_name,
                    "-",
                    "-",
                    "-",
                    "-",
                    _u("\u884c\u30c7\u30fc\u30bf\u306a\u3057"),
                    "-",
                    "-",
                ]
            )
            continue

        for module_row in sorted(module.rows, key=lambda row: row.row_order):
            rows.append(
                [
                    module.item_order,
                    module_status,
                    module.module_key,
                    module.module_name,
                    module_row.row_order,
                    module_row.major_no or "",
                    module_row.middle_no or "",
                    module_row.minor_no or "",
                    module_row.work_text or "",
                    module_row.expected_result or "",
                    module_row.command_text or "",
                ]
            )

    for row_index, values in enumerate(rows, start=1):
        _write_row(sheet, row_index, values)
        if values and len(values) == 1:
            sheet.cell(row=row_index, column=1).font = Font(bold=True, size=14)
        if values == row_header:
            _style_heading(sheet, row_index)

    for column_letter, width in {
        "A": 14,
        "B": 14,
        "C": 18,
        "D": 34,
        "E": 12,
        "F": 10,
        "G": 10,
        "H": 10,
        "I": 56,
        "J": 34,
        "K": 42,
    }.items():
        sheet.column_dimensions[column_letter].width = width
    sheet.freeze_panes = "A11"


def build_case_doc_workbook_bytes(
    context: CaseDocResolveContextData,
    source_doc: SourceDocDetailData | None = None,
) -> bytes:
    """Build an xlsm workbook by copying the configured template."""

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"case document template was not found: {TEMPLATE_PATH}")

    workbook = load_workbook(TEMPLATE_PATH, keep_vba=True)
    placeholder_values = _build_placeholder_values(context)
    for sheet in workbook.worksheets:
        if sheet.title != RESOLVED_VALUES_SHEET_NAME:
            _replace_placeholders(sheet, placeholder_values)

    if RESOLVED_VALUES_SHEET_NAME in workbook.sheetnames:
        resolved_sheet = workbook[RESOLVED_VALUES_SHEET_NAME]
    else:
        resolved_sheet = workbook.create_sheet(RESOLVED_VALUES_SHEET_NAME)
    _write_resolved_values_sheet(resolved_sheet, context)

    if source_doc is not None:
        if SOURCE_DOC_EXPANSION_SHEET_NAME in workbook.sheetnames:
            source_doc_sheet = workbook[SOURCE_DOC_EXPANSION_SHEET_NAME]
        else:
            source_doc_sheet = workbook.create_sheet(SOURCE_DOC_EXPANSION_SHEET_NAME)
        _write_source_doc_expansion_sheet(source_doc_sheet, source_doc)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()

