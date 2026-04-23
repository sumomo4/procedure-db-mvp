"""Tests for future Excel import helpers."""

import pytest

from app.core.excel_import import (
    build_module_create_request_from_sheet_data,
    extract_work_text_and_indent_level,
    normalize_excel_cell_text,
)


def test_normalize_excel_cell_text_trims_string_values() -> None:
    """Whitespace-only values should be treated as empty."""

    assert normalize_excel_cell_text("  sample  ") == "sample"
    assert normalize_excel_cell_text("   ") is None
    assert normalize_excel_cell_text(None) is None


def test_extract_work_text_and_indent_level_prefers_leftmost_work_column() -> None:
    """The first populated work column should define indent and text."""

    text, indent_level = extract_work_text_and_indent_level(
        {
            "E": None,
            "F": "  step text  ",
            "G": "nested text",
            "H": None,
        }
    )

    assert text == "step text"
    assert indent_level == 1


def test_extract_work_text_and_indent_level_returns_none_when_empty() -> None:
    """Empty work columns should produce no work text and no indent level."""

    text, indent_level = extract_work_text_and_indent_level(
        {
            "E": None,
            "F": " ",
            "G": None,
            "H": None,
        }
    )

    assert text is None
    assert indent_level is None


def test_extract_work_text_and_indent_level_supports_deeper_columns() -> None:
    """Columns G and H should map to deeper indent levels."""

    text_g, indent_g = extract_work_text_and_indent_level({"G": "child"})
    text_h, indent_h = extract_work_text_and_indent_level({"H": "grandchild"})

    assert (text_g, indent_g) == ("child", 2)
    assert (text_h, indent_h) == ("grandchild", 3)


def test_build_module_create_request_from_sheet_data_supports_one_device() -> None:
    """One device block should map into one normalized device header."""

    payload = build_module_create_request_from_sheet_data(
        module_name="単一装置モジュール",
        source_xlsx_path="imports/module-01.xlsm",
        created_by="tester",
        device_header_cells=[
            {
                "slot_no": 1,
                "header_time_text": "09:00",
                "target_text": "CS",
                "p_text": ">",
                "target_device_text": "device-01",
            }
        ],
        row_cells=[
            {
                "A": "1",
                "B": "1",
                "C": "1",
                "D": "Tech doc",
                "E": "show version",
                "I": "Ready",
                "device_entries": [
                    {
                        "slot_no": 1,
                        "time_text": "09:05",
                        "window_text": "STOP",
                        "p_text": ">",
                        "command_text": "show version",
                    }
                ],
            }
        ],
    )

    assert payload.module_name == "単一装置モジュール"
    assert payload.device_headers[0].target_device_text == "device-01"
    assert payload.rows[0].row_order == 1
    assert payload.rows[0].device_entries[0].command_text == "show version"


def test_build_module_create_request_from_sheet_data_supports_two_devices() -> None:
    """Two device blocks should be preserved in both header and row entries."""

    payload = build_module_create_request_from_sheet_data(
        module_name="2台モジュール",
        device_header_cells=[
            {"slot_no": 1, "target_device_text": "device-01"},
            {"slot_no": 2, "target_device_text": "device-02"},
        ],
        row_cells=[
            {
                "A": "1",
                "B": "1",
                "C": "1",
                "D": "Tech doc",
                "E": "parent",
                "device_entries": [
                    {"slot_no": 1, "window_text": "STOP", "command_text": "show ver 1"},
                    {"slot_no": 2, "window_text": "STOP", "command_text": "show ver 2"},
                ],
            }
        ],
    )

    assert [header.slot_no for header in payload.device_headers] == [1, 2]
    assert [entry.slot_no for entry in payload.rows[0].device_entries] == [1, 2]
    assert payload.rows[0].device_entries[1].command_text == "show ver 2"


def test_build_module_create_request_from_sheet_data_supports_twenty_devices() -> None:
    """Twenty device blocks should be accepted as the supported upper bound."""

    payload = build_module_create_request_from_sheet_data(
        module_name="20台モジュール",
        device_header_cells=[
            {"slot_no": slot_no, "target_device_text": f"device-{slot_no:02d}"}
            for slot_no in range(1, 21)
        ],
        row_cells=[
            {
                "E": "root",
                "device_entries": [
                    {"slot_no": slot_no, "command_text": f"cmd-{slot_no:02d}"}
                    for slot_no in range(1, 21)
                ],
            }
        ],
    )

    assert len(payload.device_headers) == 20
    assert len(payload.rows[0].device_entries) == 20


def test_build_module_create_request_from_sheet_data_rejects_more_than_twenty_devices() -> None:
    """Twenty-one device blocks should fail validation before API usage."""

    with pytest.raises(ValueError, match="must not exceed 20 slots"):
        build_module_create_request_from_sheet_data(
            module_name="21台モジュール",
            device_header_cells=[
                {"slot_no": slot_no, "target_device_text": f"device-{slot_no:02d}"}
                for slot_no in range(1, 22)
            ],
            row_cells=[{"E": "root"}],
        )


def test_build_module_create_request_from_sheet_data_maps_indent_level() -> None:
    """Excel work columns should still control work text and indent level."""

    payload = build_module_create_request_from_sheet_data(
        module_name="段落モジュール",
        row_cells=[
            {
                "A": "1",
                "B": "2",
                "C": "3",
                "G": "child step",
            }
        ],
    )

    assert payload.rows[0].work_text == "child step"
    assert payload.rows[0].indent_level == 2


def test_build_module_create_request_from_sheet_data_skips_empty_rows() -> None:
    """Completely empty rows should be ignored and row_order should be compacted."""

    payload = build_module_create_request_from_sheet_data(
        module_name="空行ありモジュール",
        row_cells=[
            {"A": None, "E": " "},
            {"A": "1", "E": "first"},
            {"A": None, "device_entries": []},
            {"A": "2", "F": "second"},
        ],
    )

    assert [row.row_order for row in payload.rows] == [1, 2]
    assert [row.work_text for row in payload.rows] == ["first", "second"]
    assert [row.indent_level for row in payload.rows] == [0, 1]
