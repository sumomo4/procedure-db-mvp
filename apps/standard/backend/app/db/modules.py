"""Database access helpers for module resources."""

from collections.abc import Sequence
from datetime import date, datetime
from difflib import SequenceMatcher
import json
import re
from typing import Any
import unicodedata

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApprovalStatusDetailData,
    ApprovalStatusHistoryItemData,
    ApprovalTransitionData,
    ModuleDiffData,
    ModuleDiffRowData,
    ModuleDiffSummaryData,
    ModuleCreateDeviceHeaderInput,
    ModuleCreateRequest,
    ModuleCreateRowDeviceEntryInput,
    ModuleDeviceHeaderData,
    ModuleDetailData,
    ModuleListData,
    ModuleListItemData,
    ModuleRowData,
    ModuleRowDeviceEntryData,
    ModuleRowImageData,
    ModuleVersionListData,
    ModuleVersionListItemData,
)


MODULE_STATUS_LABELS = {
    "draft": "作成中",
    "published": "承認済み",
    "archived": "保管済み",
}
VALID_MODULE_STATUSES = frozenset(MODULE_STATUS_LABELS)
MODULE_APPROVAL_NEXT_ACTIONS = {
    "draft": "承認または差戻し",
    "published": "保管する",
    "archived": "確認のみ",
}
MODULE_APPROVAL_ALLOWED_TRANSITIONS = {
    "draft": [("published", "承認する"), ("draft", "差戻す")],
    "published": [("archived", "保管する")],
    "archived": [],
}


def _format_updated_at(value: Any) -> str:
    """Format DB updated_at value for API responses."""

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _format_changed_at(value: Any) -> str:
    """Format DB changed_at value for API responses."""

    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _ensure_module_approval_history_table(cursor: Any) -> None:
    """Create the module approval history table when existing DB volumes predate it."""

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS proc.module_approval_status_histories (
            module_approval_status_history_id bigserial PRIMARY KEY,
            module_id bigint NOT NULL REFERENCES proc.modules (module_id) ON DELETE CASCADE,
            module_version_id bigint NOT NULL REFERENCES proc.module_versions (module_version_id) ON DELETE CASCADE,
            from_status text CHECK (from_status IN ('draft', 'published', 'archived')),
            to_status text NOT NULL CHECK (to_status IN ('draft', 'published', 'archived')),
            action_label text NOT NULL,
            changed_by text,
            changed_at timestamptz NOT NULL DEFAULT now(),
            note text
        );
        """,
        {},
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_module_approval_status_histories_module
            ON proc.module_approval_status_histories (module_id, changed_at DESC);
        """,
        {},
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_module_approval_status_histories_version
            ON proc.module_approval_status_histories (module_version_id);
        """,
        {},
    )


def _build_module_transition_data(status_value: str) -> list[ApprovalTransitionData]:
    """Build allowed transitions for a module version status."""

    return [
        ApprovalTransitionData(
            to_status=to_status,
            to_status_label=MODULE_STATUS_LABELS.get(to_status, to_status),
            action_label=action_label,
        )
        for to_status, action_label in MODULE_APPROVAL_ALLOWED_TRANSITIONS.get(status_value, [])
    ]


def _build_module_history_items(rows: list[Any]) -> list[ApprovalStatusHistoryItemData]:
    """Build module approval history response items."""

    return [
        ApprovalStatusHistoryItemData(
            history_id=row[0],
            from_status=row[1],
            from_status_label=MODULE_STATUS_LABELS.get(row[1], row[1]) if row[1] is not None else None,
            to_status=row[2],
            to_status_label=MODULE_STATUS_LABELS.get(row[2], row[2]),
            action_label=row[3],
            changed_by=row[4],
            changed_at=_format_changed_at(row[5]),
            note=row[6],
        )
        for row in rows
    ]


def _build_module_list_query(
    keyword: str | None,
    status_filter: str | None,
) -> tuple[str, dict[str, str]]:
    """Build the module list query and parameters."""

    conditions: list[str] = []
    parameters: dict[str, str] = {}

    if keyword:
        conditions.append(
            """
            (
                m.module_key ILIKE %(keyword)s
                OR m.name ILIKE %(keyword)s
                OR COALESCE(m.description, '') ILIKE %(keyword)s
                OR EXISTS (
                    SELECT 1
                    FROM proc.module_rows rx
                    WHERE rx.module_version_id = mv.module_version_id
                      AND COALESCE(rx.work_text, '') ILIKE %(keyword)s
                )
            )
            """
        )
        parameters["keyword"] = f"%{keyword}%"

    if status_filter and status_filter != "all":
        conditions.append("mv.status = %(status_filter)s")
        parameters["status_filter"] = status_filter

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            m.module_id,
            m.module_key,
            m.name AS module_name,
            m.description,
            mv.module_version_id,
            mv.version_no,
            mv.status,
            COUNT(r.module_row_id)::int AS row_count,
            COALESCE(
                (
                    SELECT r2.work_text
                    FROM proc.module_rows r2
                    WHERE r2.module_version_id = mv.module_version_id
                      AND r2.row_type = 'step'
                      AND COALESCE(r2.work_text, '') <> ''
                    ORDER BY r2.row_order
                    LIMIT 1
                ),
                ''
            ) AS first_work_text,
            mv.source_xlsx_path,
            mv.created_by,
            mv.updated_at
        FROM proc.modules m
        JOIN proc.module_versions mv
            ON mv.module_id = m.module_id
        LEFT JOIN proc.module_rows r
            ON r.module_version_id = mv.module_version_id
        {where_clause}
        GROUP BY
            m.module_id,
            m.module_key,
            m.name,
            m.description,
            mv.module_version_id,
            mv.version_no,
            mv.status,
            mv.source_xlsx_path,
            mv.created_by,
            mv.updated_at
        ORDER BY m.module_key, mv.version_no;
    """
    return query, parameters


def _build_module_detail_query(version_no: int | None = None) -> str:
    """Build the module detail query."""

    version_condition = "AND mv.version_no = %(version_no)s" if version_no is not None else ""
    version_order = "ORDER BY mv.version_no DESC" if version_no is None else ""

    return """
        WITH selected_version AS (
            SELECT
                mv.module_version_id,
                mv.module_id,
                mv.version_no,
                mv.status,
                mv.source_xlsx_path,
                mv.created_by,
                mv.header_time_text,
                mv.target_text,
                mv.common_p_text,
                mv.target_device_text,
                mv.device_headers_json,
                mv.created_at,
                mv.updated_at
            FROM proc.module_versions mv
            WHERE mv.module_id = %(module_id)s
            {version_condition}
            {version_order}
            LIMIT 1
        )
        SELECT
            m.module_id,
            m.module_key,
            m.name AS module_name,
            m.description,
            sv.module_version_id,
            sv.version_no,
            sv.status,
            sv.source_xlsx_path,
            sv.created_by,
            sv.header_time_text,
            sv.target_text,
            sv.common_p_text,
            sv.target_device_text,
            sv.device_headers_json,
            sv.created_at,
            sv.updated_at,
            r.module_row_id,
            r.row_order,
            r.row_type,
            r.major_no,
            r.middle_no,
            r.minor_no,
            r.tech_doc_text,
            r.work_text,
            r.indent_level,
            r.check_text_default,
            r.time_text,
            r.window_template_default,
            r.p_template_default,
            r.command_template_default,
            r.device_entries_json,
            COALESCE(row_images.images_json, '[]'::jsonb) AS images_json
        FROM proc.modules m
        JOIN selected_version sv
            ON sv.module_id = m.module_id
        LEFT JOIN proc.module_rows r
            ON r.module_version_id = sv.module_version_id
        LEFT JOIN LATERAL (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'module_row_image_id', mri.module_row_image_id,
                    'image_key', mri.image_key,
                    'image_path', mri.image_path,
                    'anchor_cell', mri.anchor_cell,
                    'offset_x_px', mri.offset_x_px,
                    'offset_y_px', mri.offset_y_px,
                    'width_px', mri.width_px,
                    'height_px', mri.height_px,
                    'image_order', mri.image_order
                )
                ORDER BY mri.image_order, mri.module_row_image_id
            ) AS images_json
            FROM proc.module_row_images mri
            WHERE mri.module_row_id = r.module_row_id
        ) row_images ON true
        WHERE m.module_id = %(module_id)s
        ORDER BY r.row_order;
    """.format(version_condition=version_condition, version_order=version_order)


def _fetch_module_detail_rows(connection: Any, module_id: int, version_no: int | None = None) -> list[tuple[Any, ...]]:
    """Fetch raw rows used to build a module detail payload."""

    parameters = {"module_id": str(module_id)}
    if version_no is not None:
        parameters["version_no"] = str(version_no)

    with connection.cursor() as cursor:
        cursor.execute(_build_module_detail_query(version_no), parameters)
        return cursor.fetchall()


def _coerce_json_array(value: Any) -> list[dict[str, Any]]:
    """Convert psycopg JSONB values or test strings to a list of dictionaries."""

    if value in (None, ""):
        return []
    if isinstance(value, str):
        parsed = json.loads(value)
    else:
        parsed = value
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _build_legacy_device_header(
    header_time_text: str | None,
    target_text: str | None,
    common_p_text: str | None,
    target_device_text: str | None,
) -> list[dict[str, Any]]:
    return [
        {
            "slot_no": 1,
            "header_time_text": header_time_text,
            "target_text": target_text,
            "p_text": common_p_text,
            "target_device_text": target_device_text,
        }
    ]


def _build_legacy_device_entry(
    time_text: str | None,
    window_text: str | None,
    p_text: str | None,
    command_text: str | None,
) -> list[dict[str, Any]]:
    return [
        {
            "slot_no": 1,
            "time_text": time_text,
            "window_text": window_text,
            "p_text": p_text,
            "command_text": command_text,
        }
    ]


def _map_device_headers(
    value: Any,
    header_time_text: str | None,
    target_text: str | None,
    common_p_text: str | None,
    target_device_text: str | None,
) -> list[ModuleDeviceHeaderData]:
    raw_headers = _coerce_json_array(value) or _build_legacy_device_header(
        header_time_text,
        target_text,
        common_p_text,
        target_device_text,
    )
    return [
        ModuleDeviceHeaderData(
            slot_no=int(item.get("slot_no", 1)),
            header_time_text=item.get("header_time_text"),
            target_text=item.get("target_text"),
            p_text=item.get("p_text"),
            target_device_text=item.get("target_device_text"),
        )
        for item in sorted(raw_headers, key=lambda item: int(item.get("slot_no", 1)))
    ]


def _map_device_entries(
    value: Any,
    time_text: str | None,
    window_text: str | None,
    p_text: str | None,
    command_text: str | None,
) -> list[ModuleRowDeviceEntryData]:
    raw_entries = _coerce_json_array(value) or _build_legacy_device_entry(
        time_text,
        window_text,
        p_text,
        command_text,
    )
    return [
        ModuleRowDeviceEntryData(
            slot_no=int(item.get("slot_no", 1)),
            time_text=item.get("time_text"),
            window_text=item.get("window_text"),
            p_text=item.get("p_text"),
            command_text=item.get("command_text"),
        )
        for item in sorted(raw_entries, key=lambda item: int(item.get("slot_no", 1)))
    ]


def _map_row_images(value: Any) -> list[ModuleRowImageData]:
    """Convert row image JSON values to response payloads."""

    raw_images = sorted(
        _coerce_json_array(value),
        key=lambda item: (int(item.get("image_order") or 1), int(item.get("module_row_image_id") or 0)),
    )
    return [
        ModuleRowImageData(
            module_row_image_id=int(item["module_row_image_id"]),
            image_key=str(item["image_key"]),
            image_path=str(item["image_path"]),
            anchor_cell=str(item["anchor_cell"]),
            offset_x_px=int(item.get("offset_x_px") or 0),
            offset_y_px=int(item.get("offset_y_px") or 0),
            width_px=int(item["width_px"]) if item.get("width_px") is not None else None,
            height_px=int(item["height_px"]) if item.get("height_px") is not None else None,
            image_order=int(item.get("image_order") or 1),
        )
        for item in raw_images
        if item.get("module_row_image_id") is not None
        and item.get("image_key") is not None
        and item.get("image_path") is not None
        and item.get("anchor_cell") is not None
    ]


def _normalize_device_headers(payload: ModuleCreateRequest) -> list[ModuleCreateDeviceHeaderInput]:
    """Return normalized device header inputs with a slot 1 fallback."""

    if payload.device_headers:
        return sorted(payload.device_headers, key=lambda item: item.slot_no)
    return [
        ModuleCreateDeviceHeaderInput(
            slot_no=1,
            header_time_text=payload.header_time_text,
            target_text=payload.target_text,
            p_text=payload.common_p_text,
            target_device_text=payload.target_device_text,
        )
    ]


def _normalize_row_device_entries(
    row: Any,
    device_slot_nos: set[int],
) -> list[ModuleCreateRowDeviceEntryInput]:
    """Return normalized row device entries with a slot 1 fallback."""

    entries = (
        sorted(row.device_entries, key=lambda item: item.slot_no)
        if row.device_entries
        else [
            ModuleCreateRowDeviceEntryInput(
                slot_no=1,
                time_text=row.time_text,
                window_text=row.window_text,
                p_text=row.p_text,
                command_text=row.command_text,
            )
        ]
    )

    invalid_slot_nos = [entry.slot_no for entry in entries if entry.slot_no not in device_slot_nos]
    if invalid_slot_nos:
        raise ValueError("row device_entries must reference configured device_headers.")
    return entries


def _map_module_detail_rows(rows: Sequence[tuple[Any, ...]]) -> ModuleDetailData | None:
    """Convert raw module detail rows to response data."""

    if not rows:
        return None

    def field(row: tuple[Any, ...], index: int, default: Any = None) -> Any:
        if index < 0 or index >= len(row):
            return default
        return row[index]

    first_row = rows[0]
    uses_json_columns = len(first_row) >= 31
    device_headers_index = 13 if uses_json_columns else -1
    created_at_index = 14 if uses_json_columns else 13
    updated_at_index = 15 if uses_json_columns else 14
    row_base_index = 16 if uses_json_columns else 15
    device_headers = _map_device_headers(
        field(first_row, device_headers_index),
        field(first_row, 9),
        field(first_row, 10),
        field(first_row, 11),
        field(first_row, 12),
    )
    module_rows = [
        ModuleRowData(
            module_row_id=field(row, row_base_index),
            row_order=field(row, row_base_index + 1),
            row_type=field(row, row_base_index + 2),
            major_no=field(row, row_base_index + 3),
            middle_no=field(row, row_base_index + 4),
            minor_no=field(row, row_base_index + 5),
            tech_doc_text=field(row, row_base_index + 6),
            work_text=field(row, row_base_index + 7),
            indent_level=field(row, row_base_index + 8),
            expected_result=field(row, row_base_index + 9),
            time_text=field(row, row_base_index + 10),
            window_text=field(row, row_base_index + 11),
            p_text=field(row, row_base_index + 12),
            command_text=field(row, row_base_index + 13),
            note=field(row, row_base_index + 6),
            device_entries=_map_device_entries(
                field(row, row_base_index + 14),
                field(row, row_base_index + 10),
                field(row, row_base_index + 11),
                field(row, row_base_index + 12),
                field(row, row_base_index + 13),
            ),
            images=_map_row_images(field(row, row_base_index + 15)),
        )
        for row in rows
        if field(row, row_base_index) is not None
    ]

    return ModuleDetailData(
        module_id=field(first_row, 0),
        module_key=field(first_row, 1),
        module_name=field(first_row, 2),
        description=field(first_row, 3),
        module_version_id=field(first_row, 4),
        version_no=field(first_row, 5),
        status=field(first_row, 6),
        status_label=MODULE_STATUS_LABELS.get(field(first_row, 6), field(first_row, 6)),
        row_count=len(module_rows),
        source_xlsx_path=field(first_row, 7),
        created_by=field(first_row, 8),
        header_time_text=field(first_row, 9),
        target_text=field(first_row, 10),
        common_p_text=field(first_row, 11),
        target_device_text=field(first_row, 12),
        device_headers=device_headers,
        created_at=_format_updated_at(field(first_row, created_at_index)),
        updated_at=_format_updated_at(field(first_row, updated_at_index)),
        rows=module_rows,
    )


def _normalize_diff_text(value: str | None) -> str:
    """Normalize text before row similarity comparison."""

    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\u3000", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().casefold()


def _row_device_entry_tokens(row: ModuleRowData) -> list[str]:
    """Build deterministic tokens for device-specific row values."""

    return [
        "|".join(
            [
                str(entry.slot_no),
                _normalize_diff_text(entry.time_text),
                _normalize_diff_text(entry.window_text),
                _normalize_diff_text(entry.p_text),
                _normalize_diff_text(entry.command_text),
            ]
        )
        for entry in sorted(row.device_entries, key=lambda item: item.slot_no)
    ]


def _row_image_tokens(row: ModuleRowData) -> list[str]:
    """Build deterministic tokens for image metadata."""

    return [
        "|".join(
            [
                _normalize_diff_text(image.image_key),
                _normalize_diff_text(image.anchor_cell),
                str(image.width_px or ""),
                str(image.height_px or ""),
                str(image.image_order),
            ]
        )
        for image in sorted(row.images, key=lambda item: (item.image_order, item.image_key))
    ]


def _row_fingerprint(row: ModuleRowData) -> str:
    """Build a normalized text fingerprint for exact row matching."""

    parts = [
        _normalize_diff_text(row.row_type),
        _normalize_diff_text(row.tech_doc_text),
        _normalize_diff_text(row.work_text),
        _normalize_diff_text(row.expected_result),
        _normalize_diff_text(row.time_text),
        _normalize_diff_text(row.window_text),
        _normalize_diff_text(row.p_text),
        _normalize_diff_text(row.command_text),
        *_row_device_entry_tokens(row),
    ]
    return "\n".join(part for part in parts if part)


def _row_similarity_text(row: ModuleRowData) -> str:
    """Build text used for fuzzy row matching."""

    return _row_fingerprint(row)


def _is_blank_diff_row(row: ModuleRowData) -> bool:
    """Return whether a row should be treated as an inserted/removed blank row."""

    content_parts = [
        row.major_no,
        row.middle_no,
        row.minor_no,
        row.tech_doc_text,
        row.work_text,
        row.expected_result,
        row.time_text,
        row.window_text,
        row.p_text,
        row.command_text,
        row.note,
    ]
    return (
        not any(_normalize_diff_text(part) for part in content_parts)
        and not _row_device_entry_tokens(row)
        and not _row_image_tokens(row)
    )


def _row_similarity(before: ModuleRowData, after: ModuleRowData) -> float:
    """Return similarity ratio between two rows."""

    before_text = _row_similarity_text(before)
    after_text = _row_similarity_text(after)
    if not before_text or not after_text:
        return 0.0
    return SequenceMatcher(None, before_text, after_text).ratio()


def _row_changed_fields(before: ModuleRowData, after: ModuleRowData) -> list[str]:
    """Return changed field names between matched rows."""

    changed_fields: list[str] = []
    scalar_fields = [
        "row_type",
        "major_no",
        "middle_no",
        "minor_no",
        "tech_doc_text",
        "work_text",
        "indent_level",
        "expected_result",
        "time_text",
        "window_text",
        "p_text",
        "command_text",
        "note",
    ]
    for field_name in scalar_fields:
        if getattr(before, field_name) != getattr(after, field_name):
            changed_fields.append(field_name)

    if _row_device_entry_tokens(before) != _row_device_entry_tokens(after):
        changed_fields.append("device_entries")

    if _row_image_tokens(before) != _row_image_tokens(after):
        changed_fields.append("images")

    return changed_fields


def _match_module_diff_rows(
    before_rows: Sequence[ModuleRowData],
    after_rows: Sequence[ModuleRowData],
    similarity_threshold: float = 0.75,
    row_order_window: int = 5,
) -> list[tuple[ModuleRowData | None, ModuleRowData | None, float | None]]:
    """Match rows by exact fingerprint first, then nearby similarity."""

    matched_before_ids: set[int] = set()
    matched_after_ids: set[int] = set()
    matched_pairs: list[tuple[ModuleRowData | None, ModuleRowData | None, float | None]] = []

    after_by_fingerprint: dict[str, list[ModuleRowData]] = {}
    for after in after_rows:
        fingerprint = _row_fingerprint(after)
        if fingerprint and not _is_blank_diff_row(after):
            after_by_fingerprint.setdefault(fingerprint, []).append(after)

    for before in sorted(before_rows, key=lambda item: item.row_order):
        fingerprint = _row_fingerprint(before)
        if not fingerprint or _is_blank_diff_row(before):
            continue

        candidates = [
            after
            for after in after_by_fingerprint.get(fingerprint, [])
            if after.module_row_id not in matched_after_ids
        ]
        if not candidates:
            continue

        best_candidate = min(candidates, key=lambda item: abs(item.row_order - before.row_order))
        matched_before_ids.add(before.module_row_id)
        matched_after_ids.add(best_candidate.module_row_id)
        matched_pairs.append((before, best_candidate, 1.0))

    fuzzy_candidates: list[tuple[float, int, ModuleRowData, ModuleRowData]] = []
    for before in before_rows:
        if before.module_row_id in matched_before_ids or _is_blank_diff_row(before):
            continue
        for after in after_rows:
            if after.module_row_id in matched_after_ids or _is_blank_diff_row(after):
                continue
            row_distance = abs(after.row_order - before.row_order)
            if row_distance > row_order_window:
                continue
            similarity = _row_similarity(before, after)
            if similarity >= similarity_threshold:
                fuzzy_candidates.append((similarity, row_distance, before, after))

    for similarity, _row_distance, before, after in sorted(fuzzy_candidates, key=lambda item: (-item[0], item[1])):
        if before.module_row_id in matched_before_ids or after.module_row_id in matched_after_ids:
            continue
        matched_before_ids.add(before.module_row_id)
        matched_after_ids.add(after.module_row_id)
        matched_pairs.append((before, after, round(similarity, 4)))

    for before in before_rows:
        if before.module_row_id not in matched_before_ids:
            matched_pairs.append((before, None, None))

    for after in after_rows:
        if after.module_row_id not in matched_after_ids:
            matched_pairs.append((None, after, None))

    return sorted(
        matched_pairs,
        key=lambda pair: (
            pair[1].row_order if pair[1] is not None else pair[0].row_order if pair[0] is not None else 0,
            pair[0].row_order if pair[0] is not None else 10**9,
            pair[1].row_order if pair[1] is not None else 10**9,
        ),
    )


def build_module_diff_data(before: ModuleDetailData, after: ModuleDetailData) -> ModuleDiffData:
    """Build structured diff data between two module versions."""

    diff_rows: list[ModuleDiffRowData] = []
    for before_row, after_row, similarity in _match_module_diff_rows(before.rows, after.rows):
        if before_row is None and after_row is None:
            continue

        if before_row is None:
            status = "added"
            changed_fields: list[str] = []
            row_key = f"added:{after_row.row_order if after_row is not None else 0}"
        elif after_row is None:
            status = "removed"
            changed_fields = []
            row_key = f"removed:{before_row.row_order}"
        else:
            changed_fields = _row_changed_fields(before_row, after_row)
            status = "changed" if changed_fields else "unchanged"
            row_key = f"row_order:{before_row.row_order}->{after_row.row_order}"

        diff_rows.append(
            ModuleDiffRowData(
                status=status,
                row_key=row_key,
                before=before_row,
                after=after_row,
                changed_fields=changed_fields,
                similarity=similarity,
            )
        )

    summary = ModuleDiffSummaryData(
        added_count=sum(1 for row in diff_rows if row.status == "added"),
        removed_count=sum(1 for row in diff_rows if row.status == "removed"),
        changed_count=sum(1 for row in diff_rows if row.status == "changed"),
        unchanged_count=sum(1 for row in diff_rows if row.status == "unchanged"),
    )

    return ModuleDiffData(
        module_id=after.module_id,
        module_key=after.module_key,
        module_name=after.module_name,
        from_version=before.version_no,
        to_version=after.version_no,
        summary=summary,
        rows=diff_rows,
    )


def _normalize_module_key(module_key: str | None) -> str | None:
    """Normalize module key text."""

    if module_key is None:
        return None

    normalized_key = module_key.strip().upper()
    if not normalized_key:
        raise ValueError("module_key must not be blank.")
    return normalized_key


def _validate_module_create_request(payload: ModuleCreateRequest) -> None:
    """Validate create payload with business rules."""

    if not payload.module_name.strip():
        raise ValueError("module_name must not be blank.")

    row_orders = [row.row_order for row in payload.rows]
    if len(row_orders) != len(set(row_orders)):
        raise ValueError("row_order must be unique within rows.")

    device_headers = _normalize_device_headers(payload)
    device_slot_nos = [header.slot_no for header in device_headers]
    if len(device_slot_nos) != len(set(device_slot_nos)):
        raise ValueError("slot_no must be unique within device_headers.")
    if len(device_slot_nos) > 20:
        raise ValueError("device_headers must not exceed 20 slots.")

    allowed_slot_nos = set(device_slot_nos)
    for row in payload.rows:
        row_slot_nos = [entry.slot_no for entry in _normalize_row_device_entries(row, allowed_slot_nos)]
        if len(row_slot_nos) != len(set(row_slot_nos)):
            raise ValueError("slot_no must be unique within row device_entries.")
        image_keys = [image.image_key for image in row.images]
        if len(image_keys) != len(set(image_keys)):
            raise ValueError("image_key must be unique within row images.")


def _generate_next_module_key(cursor: Any) -> str:
    """Generate the next sequential module key."""

    cursor.execute(
        """
        SELECT COALESCE(
            MAX((regexp_match(module_key, '^MOD-(\\d+)$'))[1]::int),
            0
        )
        FROM proc.modules
        WHERE module_key ~ '^MOD-\\d+$';
        """,
        {},
    )
    row = cursor.fetchone()
    next_no = int(row[0]) + 1 if row and row[0] is not None else 1
    return f"MOD-{next_no:03d}"


def _find_module_id_by_key(cursor: Any, module_key: str) -> int | None:
    """Return module_id for an existing module key."""

    cursor.execute(
        "SELECT module_id FROM proc.modules WHERE module_key = %(module_key)s;",
        {"module_key": module_key},
    )
    row = cursor.fetchone()
    return int(row[0]) if row is not None else None


def _next_module_version_no(cursor: Any, module_id: int) -> int:
    """Return the next module version number."""

    cursor.execute(
        """
        SELECT COALESCE(MAX(version_no), 0) + 1
        FROM proc.module_versions
        WHERE module_id = %(module_id)s;
        """,
        {"module_id": module_id},
    )
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else 1


def _has_draft_module_version(cursor: Any, module_id: int) -> bool:
    """Return whether the module already has a draft version."""

    cursor.execute(
        """
        SELECT 1
        FROM proc.module_versions
        WHERE module_id = %(module_id)s
          AND status = 'draft'
        LIMIT 1;
        """,
        {"module_id": module_id},
    )
    return cursor.fetchone() is not None


def list_modules(
    settings: AppSettings,
    keyword: str | None = None,
    status_filter: str | None = None,
) -> ModuleListData:
    """Read modules from PostgreSQL."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    query, parameters = _build_module_list_query(keyword, status_filter)

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, parameters)
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Module list query failed.") from exception

    items = [
        ModuleListItemData(
            module_id=row[0],
            module_key=row[1],
            module_name=row[2],
            description=row[3],
            module_version_id=row[4],
            version_no=row[5],
            status=row[6],
            status_label=MODULE_STATUS_LABELS.get(row[6], row[6]),
            row_count=row[7],
            first_work_text=row[8] or None,
            source_xlsx_path=row[9],
            created_by=row[10],
            updated_at=_format_updated_at(row[11]),
        )
        for row in rows
    ]

    return ModuleListData(items=items)


def get_module_detail(settings: AppSettings, module_id: int, version_no: int | None = None) -> ModuleDetailData | None:
    """Read the latest module version and rows from PostgreSQL."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            rows = _fetch_module_detail_rows(connection, module_id, version_no)
    except Exception as exception:
        raise DatabaseConnectionError("モジュール詳細の取得に失敗しました。") from exception

    return _map_module_detail_rows(rows)


def list_module_versions(settings: AppSettings, module_id: int) -> ModuleVersionListData | None:
    """Read all versions for one module."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        m.module_id,
                        m.module_key,
                        m.name,
                        mv.module_version_id,
                        mv.version_no,
                        mv.status,
                        COUNT(r.module_row_id)::int AS row_count,
                        mv.source_xlsx_path,
                        mv.created_by,
                        mv.created_at,
                        mv.updated_at
                    FROM proc.modules m
                    JOIN proc.module_versions mv
                        ON mv.module_id = m.module_id
                    LEFT JOIN proc.module_rows r
                        ON r.module_version_id = mv.module_version_id
                    WHERE m.module_id = %(module_id)s
                    GROUP BY
                        m.module_id,
                        m.module_key,
                        m.name,
                        mv.module_version_id,
                        mv.version_no,
                        mv.status,
                        mv.source_xlsx_path,
                        mv.created_by,
                        mv.created_at,
                        mv.updated_at
                    ORDER BY mv.version_no DESC;
                    """,
                    {"module_id": module_id},
                )
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Module version list query failed.") from exception

    if not rows:
        return None

    return ModuleVersionListData(
        module_id=rows[0][0],
        module_key=rows[0][1],
        module_name=rows[0][2],
        items=[
            ModuleVersionListItemData(
                module_version_id=row[3],
                version_no=row[4],
                status=row[5],
                status_label=MODULE_STATUS_LABELS.get(row[5], row[5]),
                row_count=row[6],
                source_xlsx_path=row[7],
                created_by=row[8],
                created_at=_format_updated_at(row[9]),
                updated_at=_format_updated_at(row[10]),
            )
            for row in rows
        ],
    )


def get_module_diff(
    settings: AppSettings,
    module_id: int,
    from_version: int,
    to_version: int,
) -> ModuleDiffData | None:
    """Read two module versions and return a structured diff."""

    before = get_module_detail(settings, module_id, from_version)
    after = get_module_detail(settings, module_id, to_version)
    if before is None or after is None:
        return None
    return build_module_diff_data(before, after)


def get_module_version_status(
    settings: AppSettings,
    module_id: int,
    version_no: int,
) -> ApprovalStatusDetailData | None:
    """Read one module version approval status detail."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    query = """
        SELECT
            m.module_id,
            m.module_key,
            m.name,
            m.description,
            mv.module_version_id,
            mv.version_no,
            mv.status,
            mv.change_note,
            mv.created_by,
            mv.updated_at,
            COUNT(r.module_row_id)::int AS row_count
        FROM proc.modules m
        JOIN proc.module_versions mv
            ON mv.module_id = m.module_id
        LEFT JOIN proc.module_rows r
            ON r.module_version_id = mv.module_version_id
        WHERE
            m.module_id = %(module_id)s
            AND mv.version_no = %(version_no)s
        GROUP BY
            m.module_id,
            m.module_key,
            m.name,
            m.description,
            mv.module_version_id,
            mv.version_no,
            mv.status,
            mv.change_note,
            mv.created_by,
            mv.updated_at;
    """

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                _ensure_module_approval_history_table(cursor)
                cursor.execute(query, {"module_id": module_id, "version_no": version_no})
                row = cursor.fetchone()
                if row is None:
                    return None

                module_version_id = int(row[4])
                cursor.execute(
                    """
                    SELECT
                        module_approval_status_history_id,
                        from_status,
                        to_status,
                        action_label,
                        changed_by,
                        changed_at,
                        note
                    FROM proc.module_approval_status_histories
                    WHERE module_version_id = %(module_version_id)s
                    ORDER BY changed_at DESC, module_approval_status_history_id DESC;
                    """,
                    {"module_version_id": module_version_id},
                )
                history_rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Module approval status detail query failed.") from exception

    return ApprovalStatusDetailData(
        target_id=row[0],
        target_key=row[1],
        target_name=row[2],
        target_type="module",
        version_no=row[5],
        status=row[6],
        status_label=MODULE_STATUS_LABELS.get(row[6], row[6]),
        next_action=MODULE_APPROVAL_NEXT_ACTIONS.get(row[6], "確認のみ"),
        module_count=1,
        enabled_module_count=1,
        module_names=[row[2]],
        description=row[3],
        change_note=row[7],
        created_by=row[8],
        updated_at=_format_updated_at(row[9]),
        allowed_transitions=_build_module_transition_data(row[6]),
        history=_build_module_history_items(history_rows),
    )


def update_module_version_status(
    settings: AppSettings,
    module_id: int,
    version_no: int,
    to_status: str,
    changed_by: str | None = None,
    note: str | None = None,
) -> ApprovalStatusDetailData | None:
    """Update one module version approval status."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                _ensure_module_approval_history_table(cursor)
                cursor.execute(
                    """
                    SELECT
                        module_version_id,
                        status
                    FROM proc.module_versions
                    WHERE
                        module_id = %(module_id)s
                        AND version_no = %(version_no)s;
                    """,
                    {"module_id": module_id, "version_no": version_no},
                )
                current_row = cursor.fetchone()
                if current_row is None:
                    return None

                module_version_id = int(current_row[0])
                current_status = str(current_row[1])
                allowed_transitions = MODULE_APPROVAL_ALLOWED_TRANSITIONS.get(current_status, [])
                allowed_targets = {status_value for status_value, _ in allowed_transitions}
                if to_status not in allowed_targets:
                    raise ValueError(
                        f"status transition from {current_status} to {to_status} is not allowed."
                    )
                if current_status == "draft" and to_status == "draft" and not (note or "").strip():
                    raise ValueError("差戻し理由を入力してください。")
                action_label = next(
                    label for status_value, label in allowed_transitions if status_value == to_status
                )

                cursor.execute(
                    """
                    UPDATE proc.module_versions
                    SET
                        status = %(to_status)s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE module_version_id = %(module_version_id)s;
                    """,
                    {"to_status": to_status, "module_version_id": module_version_id},
                )
                cursor.execute(
                    """
                    INSERT INTO proc.module_approval_status_histories (
                        module_id,
                        module_version_id,
                        from_status,
                        to_status,
                        action_label,
                        changed_by,
                        note
                    )
                    VALUES (
                        %(module_id)s,
                        %(module_version_id)s,
                        %(from_status)s,
                        %(to_status)s,
                        %(action_label)s,
                        %(changed_by)s,
                        %(note)s
                    );
                    """,
                    {
                        "module_id": module_id,
                        "module_version_id": module_version_id,
                        "from_status": current_status,
                        "to_status": to_status,
                        "action_label": action_label,
                        "changed_by": changed_by,
                        "note": note,
                    },
                )
            connection.commit()
    except ValueError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("Module approval status update failed.") from exception

    return get_module_version_status(settings, module_id, version_no)


def get_module_row_image(settings: AppSettings, module_row_image_id: int) -> ModuleRowImageData | None:
    """Read metadata for one module row image."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        module_row_image_id,
                        image_key,
                        image_path,
                        anchor_cell,
                        offset_x_px,
                        offset_y_px,
                        width_px,
                        height_px,
                        image_order
                    FROM proc.module_row_images
                    WHERE module_row_image_id = %(module_row_image_id)s;
                    """,
                    {"module_row_image_id": module_row_image_id},
                )
                row = cursor.fetchone()
    except Exception as exception:
        raise DatabaseConnectionError("モジュール行画像の取得に失敗しました。") from exception

    if row is None:
        return None

    return ModuleRowImageData(
        module_row_image_id=int(row[0]),
        image_key=str(row[1]),
        image_path=str(row[2]),
        anchor_cell=str(row[3]),
        offset_x_px=int(row[4] or 0),
        offset_y_px=int(row[5] or 0),
        width_px=int(row[6]) if row[6] is not None else None,
        height_px=int(row[7]) if row[7] is not None else None,
        image_order=int(row[8] or 1),
    )


def create_module(settings: AppSettings, payload: ModuleCreateRequest) -> ModuleDetailData:
    """Create a module, its initial version, and module rows."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    _validate_module_create_request(payload)

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            module_id: int | None = None
            module_version_no = 1
            normalized_device_headers = _normalize_device_headers(payload)
            primary_device_header = normalized_device_headers[0]
            device_slot_nos = {header.slot_no for header in normalized_device_headers}

            with connection.cursor() as cursor:
                normalized_module_key = _normalize_module_key(payload.module_key)
                if normalized_module_key is None:
                    normalized_module_key = _generate_next_module_key(cursor)
                    existing_module_id = None
                else:
                    existing_module_id = _find_module_id_by_key(cursor, normalized_module_key)

                if existing_module_id is None:
                    cursor.execute(
                        """
                        INSERT INTO proc.modules (module_key, name, description)
                        VALUES (%(module_key)s, %(module_name)s, %(description)s)
                        RETURNING module_id, module_key;
                        """,
                        {
                            "module_key": normalized_module_key,
                            "module_name": payload.module_name.strip(),
                            "description": payload.description,
                        },
                    )
                    inserted_module = cursor.fetchone()
                    if inserted_module is None:
                        raise DatabaseConnectionError("Module create failed.")

                    module_id = int(inserted_module[0])
                    module_version_no = 1
                else:
                    module_id = existing_module_id
                    if _has_draft_module_version(cursor, module_id):
                        raise ValueError("draft module version already exists.")
                    module_version_no = _next_module_version_no(cursor, module_id)
                    cursor.execute(
                        """
                        UPDATE proc.modules
                        SET
                            name = %(module_name)s,
                            description = %(description)s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE module_id = %(module_id)s;
                        """,
                        {
                            "module_id": module_id,
                            "module_name": payload.module_name.strip(),
                            "description": payload.description,
                        },
                    )

                cursor.execute(
                    """
                    INSERT INTO proc.module_versions (
                        module_id,
                        version_no,
                        status,
                        change_note,
                        source_xlsx_path,
                        source_sha256,
                        created_by,
                        header_time_text,
                        target_text,
                        common_p_text,
                        target_device_text,
                        device_headers_json
                    )
                    VALUES (
                        %(module_id)s,
                        %(version_no)s,
                        'draft',
                        %(change_note)s,
                        %(source_xlsx_path)s,
                        %(source_sha256)s,
                        %(created_by)s,
                        %(header_time_text)s,
                        %(target_text)s,
                        %(common_p_text)s,
                        %(target_device_text)s,
                        %(device_headers_json)s
                    )
                    RETURNING module_version_id;
                    """,
                    {
                        "module_id": module_id,
                        "version_no": module_version_no,
                        "change_note": payload.change_note,
                        "source_xlsx_path": payload.source_xlsx_path,
                        "source_sha256": payload.source_sha256,
                        "created_by": payload.created_by,
                        "header_time_text": primary_device_header.header_time_text,
                        "target_text": primary_device_header.target_text,
                        "common_p_text": primary_device_header.p_text,
                        "target_device_text": primary_device_header.target_device_text,
                        "device_headers_json": json.dumps(
                            [
                                {
                                    "slot_no": header.slot_no,
                                    "header_time_text": header.header_time_text,
                                    "target_text": header.target_text,
                                    "p_text": header.p_text,
                                    "target_device_text": header.target_device_text,
                                }
                                for header in normalized_device_headers
                            ]
                        ),
                    },
                )
                inserted_version = cursor.fetchone()
                if inserted_version is None:
                    raise DatabaseConnectionError("Module create failed.")
                module_version_id = int(inserted_version[0])

                for row in sorted(payload.rows, key=lambda item: item.row_order):
                    normalized_row_device_entries = _normalize_row_device_entries(row, device_slot_nos)
                    primary_row_device_entry = normalized_row_device_entries[0]
                    cursor.execute(
                        """
                        INSERT INTO proc.module_rows (
                            module_version_id,
                            row_order,
                            row_type,
                            major_no,
                            middle_no,
                            minor_no,
                            tech_doc_text,
                            work_text,
                            indent_level,
                            check_text_default,
                            time_text,
                            window_template_default,
                            p_template_default,
                            command_template_default,
                            device_entries_json
                        )
                        VALUES (
                            %(module_version_id)s,
                            %(row_order)s,
                            %(row_type)s,
                            %(major_no)s,
                            %(middle_no)s,
                            %(minor_no)s,
                            %(tech_doc_text)s,
                            %(work_text)s,
                            %(indent_level)s,
                            %(expected_result)s,
                            %(time_text)s,
                            %(window_text)s,
                            %(p_text)s,
                            %(command_text)s,
                            %(device_entries_json)s
                        )
                        RETURNING module_row_id;
                        """,
                        {
                            "module_version_id": module_version_id,
                            "row_order": row.row_order,
                            "row_type": row.row_type,
                            "major_no": row.major_no,
                            "middle_no": row.middle_no,
                            "minor_no": row.minor_no,
                            "tech_doc_text": row.tech_doc_text,
                            "work_text": row.work_text,
                            "indent_level": row.indent_level,
                            "expected_result": row.expected_result,
                            "time_text": primary_row_device_entry.time_text,
                            "window_text": primary_row_device_entry.window_text,
                            "p_text": primary_row_device_entry.p_text,
                            "command_text": primary_row_device_entry.command_text,
                            "device_entries_json": json.dumps(
                                [
                                    {
                                        "slot_no": entry.slot_no,
                                        "time_text": entry.time_text,
                                        "window_text": entry.window_text,
                                        "p_text": entry.p_text,
                                        "command_text": entry.command_text,
                                    }
                                    for entry in normalized_row_device_entries
                                ]
                            ),
                        },
                    )
                    inserted_row = cursor.fetchone()
                    if inserted_row is None:
                        raise DatabaseConnectionError("Module create failed.")
                    module_row_id = int(inserted_row[0])

                    for image in sorted(row.images, key=lambda item: item.image_order):
                        cursor.execute(
                            """
                            INSERT INTO proc.module_row_images (
                                module_row_id,
                                image_key,
                                image_path,
                                anchor_cell,
                                offset_x_px,
                                offset_y_px,
                                width_px,
                                height_px,
                                image_order
                            )
                            VALUES (
                                %(module_row_id)s,
                                %(image_key)s,
                                %(image_path)s,
                                %(anchor_cell)s,
                                %(offset_x_px)s,
                                %(offset_y_px)s,
                                %(width_px)s,
                                %(height_px)s,
                                %(image_order)s
                            );
                            """,
                            {
                                "module_row_id": module_row_id,
                                "image_key": image.image_key,
                                "image_path": image.image_path,
                                "anchor_cell": image.anchor_cell,
                                "offset_x_px": image.offset_x_px,
                                "offset_y_px": image.offset_y_px,
                                "width_px": image.width_px,
                                "height_px": image.height_px,
                                "image_order": image.image_order,
                            },
                        )

            if module_id is None:
                raise DatabaseConnectionError("Module create failed.")

            detail_rows = _fetch_module_detail_rows(connection, module_id, module_version_no)
            connection.commit()
    except ValueError:
        raise
    except DatabaseConnectionError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("Module create failed.") from exception

    detail = _map_module_detail_rows(detail_rows)
    if detail is None:
        raise DatabaseConnectionError("Module create failed.")
    return detail
