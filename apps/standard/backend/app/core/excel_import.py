"""Helpers for future Excel module import processing."""

from collections.abc import Mapping


WORK_TEXT_COLUMNS = ("E", "F", "G", "H")


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
