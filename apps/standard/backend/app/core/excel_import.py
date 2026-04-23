"""Helpers for future Excel module import processing."""

from collections.abc import Mapping, Sequence
from typing import Any

from app.core.responses import (
    ModuleCreateDeviceHeaderInput,
    ModuleCreateRequest,
    ModuleCreateRowDeviceEntryInput,
    ModuleCreateRowInput,
)


WORK_TEXT_COLUMNS = ("E", "F", "G", "H")
COMMON_ROW_COLUMN_MAP = {
    "A": "major_no",
    "B": "middle_no",
    "C": "minor_no",
    "D": "tech_doc_text",
    "I": "expected_result",
}
MAX_DEVICE_SLOTS = 20


def normalize_excel_cell_text(value: object) -> str | None:
    """Normalize a value read from Excel into trimmed text.

    Args:
        value: Raw cell value.

    Returns:
        Trimmed text, or ``None`` when the value is empty.
    """

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None
    return text


def extract_work_text_and_indent_level(
    work_cells: Mapping[str, object | None],
) -> tuple[str | None, int | None]:
    """Resolve work text and indent level from Excel work-area columns.

    The current Excel prototypes express indentation by placing text in one of
    the work columns ``E`` through ``H``. The first non-empty column becomes the
    displayed work text and its zero-based position becomes ``indent_level``.

    Args:
        work_cells: Mapping of column letter to cell value.

    Returns:
        A tuple of ``(work_text, indent_level)``. Both values are ``None`` when
        every tracked work column is empty.
    """

    for indent_level, column_name in enumerate(WORK_TEXT_COLUMNS):
        text = normalize_excel_cell_text(work_cells.get(column_name))
        if text is not None:
            return text, indent_level
    return None, None


def _normalize_sheet_device_headers(
    raw_device_headers: Sequence[Mapping[str, object | None]],
) -> list[ModuleCreateDeviceHeaderInput]:
    """Normalize device header blocks extracted from one Excel sheet."""

    normalized_headers: list[ModuleCreateDeviceHeaderInput] = []
    slot_nos: set[int] = set()

    for raw_header in raw_device_headers:
        slot_no = int(raw_header.get("slot_no", 1))
        if slot_no > MAX_DEVICE_SLOTS:
            raise ValueError("Excel device headers must not exceed 20 slots.")
        header = ModuleCreateDeviceHeaderInput(
            slot_no=slot_no,
            header_time_text=normalize_excel_cell_text(raw_header.get("header_time_text")),
            target_text=normalize_excel_cell_text(raw_header.get("target_text")),
            p_text=normalize_excel_cell_text(raw_header.get("p_text")),
            target_device_text=normalize_excel_cell_text(raw_header.get("target_device_text")),
        )
        if (
            header.header_time_text is None
            and header.target_text is None
            and header.p_text is None
            and header.target_device_text is None
        ):
            continue
        if header.slot_no in slot_nos:
            raise ValueError("slot_no must be unique within Excel device headers.")
        slot_nos.add(header.slot_no)
        normalized_headers.append(header)

    if len(normalized_headers) > MAX_DEVICE_SLOTS:
        raise ValueError("Excel device headers must not exceed 20 slots.")

    if not normalized_headers:
        normalized_headers.append(ModuleCreateDeviceHeaderInput(slot_no=1))

    return sorted(normalized_headers, key=lambda item: item.slot_no)


def _normalize_sheet_row_device_entries(
    raw_device_entries: Sequence[Mapping[str, object | None]],
    allowed_slot_nos: set[int],
) -> list[ModuleCreateRowDeviceEntryInput]:
    """Normalize one row's device-specific command cells."""

    normalized_entries: list[ModuleCreateRowDeviceEntryInput] = []
    slot_nos: set[int] = set()

    for raw_entry in raw_device_entries:
        slot_no = int(raw_entry.get("slot_no", 1))
        if slot_no not in allowed_slot_nos:
            raise ValueError("row device entries must reference configured device headers.")

        entry = ModuleCreateRowDeviceEntryInput(
            slot_no=slot_no,
            time_text=normalize_excel_cell_text(raw_entry.get("time_text")),
            window_text=normalize_excel_cell_text(raw_entry.get("window_text")),
            p_text=normalize_excel_cell_text(raw_entry.get("p_text")),
            command_text=normalize_excel_cell_text(raw_entry.get("command_text")),
        )
        if (
            entry.time_text is None
            and entry.window_text is None
            and entry.p_text is None
            and entry.command_text is None
        ):
            continue
        if entry.slot_no in slot_nos:
            raise ValueError("slot_no must be unique within one row's Excel device entries.")
        slot_nos.add(entry.slot_no)
        normalized_entries.append(entry)

    return sorted(normalized_entries, key=lambda item: item.slot_no)


def build_module_create_request_from_sheet_data(
    *,
    module_name: str,
    row_cells: Sequence[Mapping[str, object | None]],
    device_header_cells: Sequence[Mapping[str, object | None]] = (),
    module_key: str | None = None,
    description: str | None = None,
    change_note: str | None = None,
    source_xlsx_path: str | None = None,
    source_sha256: str | None = None,
    created_by: str | None = None,
) -> ModuleCreateRequest:
    """Convert one Excel sheet's normalized cells into ``ModuleCreateRequest``.

    Args:
        module_name: Target module name.
        row_cells: Row-wise Excel cell values. Common columns use ``A`` through
            ``I`` and device-specific row data is passed via ``device_entries``.
        device_header_cells: Device header blocks for the sheet.
        module_key: Optional target module key.
        description: Optional module description.
        change_note: Optional module change note.
        source_xlsx_path: Optional source workbook path.
        source_sha256: Optional source workbook hash.
        created_by: Optional import operator.

    Returns:
        ``ModuleCreateRequest`` normalized for existing create API.
    """

    normalized_headers = _normalize_sheet_device_headers(device_header_cells)
    allowed_slot_nos = {header.slot_no for header in normalized_headers}
    normalized_rows: list[ModuleCreateRowInput] = []

    for raw_row in row_cells:
        work_text, indent_level = extract_work_text_and_indent_level(raw_row)
        common_values = {
            field_name: normalize_excel_cell_text(raw_row.get(column_name))
            for column_name, field_name in COMMON_ROW_COLUMN_MAP.items()
        }
        device_entries = _normalize_sheet_row_device_entries(
            raw_row.get("device_entries", []) or [],
            allowed_slot_nos,
        )

        if (
            work_text is None
            and all(value is None for value in common_values.values())
            and not device_entries
        ):
            continue

        normalized_rows.append(
            ModuleCreateRowInput(
                row_order=len(normalized_rows) + 1,
                row_type="step",
                major_no=common_values["major_no"],
                middle_no=common_values["middle_no"],
                minor_no=common_values["minor_no"],
                tech_doc_text=common_values["tech_doc_text"],
                work_text=work_text,
                indent_level=indent_level,
                expected_result=common_values["expected_result"],
                device_entries=device_entries,
            )
        )

    if not normalize_excel_cell_text(module_name):
        raise ValueError("module_name must not be blank.")
    if not normalized_rows:
        raise ValueError("sheet must contain at least one non-empty row.")

    return ModuleCreateRequest(
        module_key=normalize_excel_cell_text(module_key),
        module_name=normalize_excel_cell_text(module_name) or "",
        description=normalize_excel_cell_text(description),
        change_note=normalize_excel_cell_text(change_note),
        source_xlsx_path=normalize_excel_cell_text(source_xlsx_path),
        source_sha256=normalize_excel_cell_text(source_sha256),
        created_by=normalize_excel_cell_text(created_by),
        device_headers=normalized_headers,
        rows=normalized_rows,
    )
