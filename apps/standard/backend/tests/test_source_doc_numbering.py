"""Tests for source-document item numbering."""

from app.services.source_doc_numbering import SourceDocNumberingRow, assign_source_doc_numbers


def _row(
    *,
    blueprint_item_id: int,
    module_row_id: int,
    item_order: int,
    row_order: int,
    indent_level: int | None,
    work_text: str | None = "work",
    enabled: bool = True,
    row_type: str = "step",
) -> SourceDocNumberingRow:
    return SourceDocNumberingRow(
        blueprint_item_id=blueprint_item_id,
        module_row_id=module_row_id,
        item_order=item_order,
        enabled=enabled,
        row_order=row_order,
        row_type=row_type,
        indent_level=indent_level,
        work_text=work_text,
    )


def test_assign_source_doc_numbers_resets_each_enabled_module() -> None:
    """Each enabled module should start a new major number at X.0.0."""

    rows = [
        _row(blueprint_item_id=10, module_row_id=101, item_order=1, row_order=1, indent_level=None),
        _row(blueprint_item_id=10, module_row_id=102, item_order=1, row_order=2, indent_level=0),
        _row(blueprint_item_id=10, module_row_id=103, item_order=1, row_order=3, indent_level=1),
        _row(blueprint_item_id=10, module_row_id=104, item_order=1, row_order=4, indent_level=0),
        _row(blueprint_item_id=20, module_row_id=201, item_order=2, row_order=1, indent_level=None),
        _row(blueprint_item_id=20, module_row_id=202, item_order=2, row_order=2, indent_level=0),
    ]

    results = assign_source_doc_numbers(rows)

    assert [(row.major_no, row.middle_no, row.minor_no) for row in results] == [
        ("0", "0", "0"),
        ("0", "1", "1"),
        ("0", "1", "2"),
        ("0", "2", "1"),
        ("1", "0", "0"),
        ("1", "1", "1"),
    ]


def test_assign_source_doc_numbers_leaves_continuation_rows_blank() -> None:
    """G/H-equivalent continuation rows should not display a new number."""

    rows = [
        _row(blueprint_item_id=10, module_row_id=101, item_order=1, row_order=1, indent_level=None),
        _row(blueprint_item_id=10, module_row_id=102, item_order=1, row_order=2, indent_level=0),
        _row(blueprint_item_id=10, module_row_id=103, item_order=1, row_order=3, indent_level=2),
        _row(blueprint_item_id=10, module_row_id=104, item_order=1, row_order=4, indent_level=3),
    ]

    results = assign_source_doc_numbers(rows)

    assert [(row.major_no, row.middle_no, row.minor_no) for row in results] == [
        ("0", "0", "0"),
        ("0", "1", "1"),
        (None, None, None),
        (None, None, None),
    ]


def test_assign_source_doc_numbers_leaves_rows_without_work_text_blank() -> None:
    """Rows containing only checks or commands should not consume an item number."""

    rows = [
        _row(blueprint_item_id=10, module_row_id=101, item_order=1, row_order=1, indent_level=0),
        _row(blueprint_item_id=10, module_row_id=102, item_order=1, row_order=2, indent_level=0),
        _row(
            blueprint_item_id=10,
            module_row_id=103,
            item_order=1,
            row_order=3,
            indent_level=0,
            work_text=None,
        ),
        _row(blueprint_item_id=10, module_row_id=104, item_order=1, row_order=4, indent_level=1),
    ]

    results = assign_source_doc_numbers(rows)

    assert [(row.major_no, row.middle_no, row.minor_no) for row in results] == [
        ("0", "0", "0"),
        ("0", "1", "1"),
        (None, None, None),
        ("0", "1", "2"),
    ]


def test_assign_source_doc_numbers_ignores_disabled_modules_and_spacers() -> None:
    """Disabled modules should not consume a major number and spacers stay blank."""

    rows = [
        _row(
            blueprint_item_id=10,
            module_row_id=101,
            item_order=1,
            row_order=1,
            indent_level=None,
            enabled=False,
        ),
        _row(
            blueprint_item_id=20,
            module_row_id=201,
            item_order=2,
            row_order=1,
            indent_level=None,
            row_type="spacer",
        ),
        _row(blueprint_item_id=20, module_row_id=202, item_order=2, row_order=2, indent_level=None),
        _row(blueprint_item_id=20, module_row_id=203, item_order=2, row_order=3, indent_level=0),
    ]

    results = assign_source_doc_numbers(rows)

    assert [(row.major_no, row.middle_no, row.minor_no) for row in results] == [
        (None, None, None),
        (None, None, None),
        ("0", "0", "0"),
        ("0", "1", "1"),
    ]
