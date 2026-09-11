"""Assign source-document item numbers from module order and row indentation."""

from dataclasses import dataclass
from itertools import groupby
from typing import Iterable


@dataclass(frozen=True)
class SourceDocNumberingRow:
    """Minimum module-row data required for source-document numbering."""

    blueprint_item_id: int
    module_row_id: int
    item_order: int
    enabled: bool
    row_order: int
    row_type: str
    indent_level: int | None
    work_text: str | None


@dataclass(frozen=True)
class SourceDocNumberingResult:
    """Numbers assigned to one module row in one source-document version."""

    blueprint_item_id: int
    module_row_id: int
    major_no: str | None
    middle_no: str | None
    minor_no: str | None


def assign_source_doc_numbers(
    rows: Iterable[SourceDocNumberingRow],
) -> list[SourceDocNumberingResult]:
    """Assign numbers per enabled module while preserving continuation rows."""

    ordered_rows = sorted(
        rows,
        key=lambda row: (row.item_order, row.blueprint_item_id, row.row_order, row.module_row_id),
    )
    results: list[SourceDocNumberingResult] = []
    major_no = -1

    for _, grouped_rows in groupby(ordered_rows, key=lambda row: row.blueprint_item_id):
        module_rows = list(grouped_rows)
        enabled = bool(module_rows and module_rows[0].enabled)
        if enabled:
            major_no += 1

        middle_no = 0
        minor_no = 0
        header_assigned = False
        first_step_pending = False

        for row in module_rows:
            assigned_major: str | None = None
            assigned_middle: str | None = None
            assigned_minor: str | None = None

            if enabled and row.row_type != "spacer":
                if not header_assigned:
                    assigned_major = str(major_no)
                    assigned_middle = "0"
                    assigned_minor = "0"
                    header_assigned = True
                    first_step_pending = True
                elif first_step_pending:
                    middle_no = 1
                    minor_no = 1
                    assigned_major = str(major_no)
                    assigned_middle = str(middle_no)
                    assigned_minor = str(minor_no)
                    first_step_pending = False
                elif row.work_text and row.indent_level == 0:
                    middle_no += 1
                    minor_no = 1
                    assigned_major = str(major_no)
                    assigned_middle = str(middle_no)
                    assigned_minor = str(minor_no)
                elif row.work_text and row.indent_level == 1:
                    if middle_no == 0:
                        middle_no = 1
                    minor_no += 1
                    assigned_major = str(major_no)
                    assigned_middle = str(middle_no)
                    assigned_minor = str(minor_no)

            results.append(
                SourceDocNumberingResult(
                    blueprint_item_id=row.blueprint_item_id,
                    module_row_id=row.module_row_id,
                    major_no=assigned_major,
                    middle_no=assigned_middle,
                    minor_no=assigned_minor,
                )
            )

    return results
