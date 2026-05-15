"""Tests for future Excel import helpers."""

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.core.excel_import import (
    build_module_create_request_from_sheet_data,
    build_module_create_request_from_workbook_bytes,
    extract_work_text_and_indent_level,
    normalize_excel_cell_text,
)


def _create_test_workbook_bytes(
    sheet_name: str,
    rows: list[dict[str, str]],
    *,
    image_anchor_cell: str | None = None,
) -> bytes:
    """Build a minimal XLSX archive for parser tests."""

    row_xml_parts: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cell_xml_parts = []
        for cell_reference, value in row.items():
            escaped = (
                value.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            cell_xml_parts.append(
                f'<c r="{cell_reference}" t="inlineStr"><is><t>{escaped}</t></is></c>'
            )
        row_xml_parts.append(f'<row r="{row_index}">{"".join(cell_xml_parts)}</row>')

    drawing_xml = '<drawing r:id="rIdDrawing1"/>'
    worksheet_attributes = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    if image_anchor_cell is not None:
        worksheet_attributes += ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<worksheet {worksheet_attributes}>"
        f"<sheetData>{''.join(row_xml_parts)}</sheetData>"
        f"{drawing_xml if image_anchor_cell is not None else ''}"
        "</worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="'
        f"{sheet_name}"
        '" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )

    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
        if image_anchor_cell is not None:
            column_letters = "".join(character for character in image_anchor_cell if character.isalpha())
            row_digits = "".join(character for character in image_anchor_cell if character.isdigit())
            column_index = 0
            for letter in column_letters:
                column_index = column_index * 26 + (ord(letter.upper()) - ord("A") + 1)
            row_index = int(row_digits)
            worksheet_rels_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rIdDrawing1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
                'Target="../drawings/drawing1.xml"/>'
                "</Relationships>"
            )
            drawing_part_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
                'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                "<xdr:oneCellAnchor>"
                "<xdr:from>"
                f"<xdr:col>{column_index - 1}</xdr:col><xdr:colOff>9525</xdr:colOff>"
                f"<xdr:row>{row_index - 1}</xdr:row><xdr:rowOff>19050</xdr:rowOff>"
                "</xdr:from>"
                '<xdr:ext cx="95250" cy="190500"/>'
                "<xdr:pic><xdr:blipFill><a:blip r:embed=\"rIdImage1\"/></xdr:blipFill></xdr:pic>"
                "<xdr:clientData/>"
                "</xdr:oneCellAnchor>"
                "</xdr:wsDr>"
            )
            drawing_rels_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rIdImage1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                'Target="../media/image1.png"/>'
                "</Relationships>"
            )
            archive.writestr("xl/worksheets/_rels/sheet1.xml.rels", worksheet_rels_xml)
            archive.writestr("xl/drawings/drawing1.xml", drawing_part_xml)
            archive.writestr("xl/drawings/_rels/drawing1.xml.rels", drawing_rels_xml)
            archive.writestr("xl/media/image1.png", b"fake-png-bytes")

    return buffer.getvalue()


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


def test_build_module_create_request_from_workbook_bytes_supports_minimal_xlsx() -> None:
    """A minimal workbook should normalize into the create request model."""

    workbook_bytes = _create_test_workbook_bytes(
        "SheetImport",
        rows=[
            {
                "A1": "major",
                "B1": "middle",
                "C1": "minor",
                "F1": "work",
                "I1": "expected",
                "J1": "time",
                "K1": "window",
                "L1": "P",
                "M1": "command",
            },
            {
                "A2": "1",
                "B2": "1",
                "C2": "1",
                "D2": "Tech doc",
                "F2": "Check command",
                "I2": "Ready",
                "J2": "10:00",
                "K2": "STOP",
                "L2": ">",
                "M2": "show version",
            },
        ],
    )

    payload = build_module_create_request_from_workbook_bytes(
        workbook_bytes=workbook_bytes,
        filename="sample.xlsx",
        created_by="tester",
    )

    assert payload.module_name == "SheetImport"
    assert payload.source_xlsx_path == "sample.xlsx"
    assert payload.created_by == "tester"
    assert len(payload.device_headers) == 1
    assert payload.rows[0].work_text == "Check command"
    assert payload.rows[0].device_entries[0].command_text == "show version"


def test_build_module_create_request_from_workbook_bytes_extracts_row_images(tmp_path) -> None:
    """Images anchored to data rows should be saved and attached to row metadata."""

    workbook_bytes = _create_test_workbook_bytes(
        "SheetImport",
        rows=[
            {
                "A1": "major",
                "B1": "middle",
                "C1": "minor",
                "F1": "work",
            },
            {
                "A2": "1",
                "B2": "1",
                "C2": "1",
                "E2": "Step with image",
            },
        ],
        image_anchor_cell="E2",
    )

    payload = build_module_create_request_from_workbook_bytes(
        workbook_bytes=workbook_bytes,
        filename="sample.xlsx",
        image_storage_dir=tmp_path / "module_images",
    )

    assert len(payload.rows[0].images) == 1
    image = payload.rows[0].images[0]
    assert image.anchor_cell == "E2"
    assert image.offset_x_px == 1
    assert image.offset_y_px == 2
    assert image.width_px == 10
    assert image.height_px == 20
    assert image.image_path.endswith(".png")
    assert Path(image.image_path).read_bytes() == b"fake-png-bytes"


def test_build_module_create_request_from_workbook_bytes_rejects_invalid_extension() -> None:
    """Only XLSX/XLSM uploads should be accepted."""

    with pytest.raises(ValueError, match="filename must end with .xlsx or .xlsm"):
        build_module_create_request_from_workbook_bytes(
            workbook_bytes=b"sample",
            filename="sample.txt",
        )
