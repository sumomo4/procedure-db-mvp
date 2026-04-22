"""Tests for future Excel import helpers."""

from app.core.excel_import import extract_work_text_and_indent_level, normalize_excel_cell_text


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
