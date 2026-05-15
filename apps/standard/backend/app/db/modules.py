"""Database access helpers for module resources."""

from collections.abc import Sequence
from datetime import date, datetime
import json
from typing import Any

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
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
)


MODULE_STATUS_LABELS = {
    "draft": "作成中",
    "published": "承認済み",
    "archived": "保管済み",
}
VALID_MODULE_STATUSES = frozenset(MODULE_STATUS_LABELS)


def _format_updated_at(value: Any) -> str:
    """Format DB updated_at value for API responses."""

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


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


def _build_module_detail_query() -> str:
    """Build the module detail query."""

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
            ORDER BY mv.version_no DESC
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
    """


def _fetch_module_detail_rows(connection: Any, module_id: int) -> list[tuple[Any, ...]]:
    """Fetch raw rows used to build a module detail payload."""

    with connection.cursor() as cursor:
        cursor.execute(_build_module_detail_query(), {"module_id": str(module_id)})
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


def get_module_detail(settings: AppSettings, module_id: int) -> ModuleDetailData | None:
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
            rows = _fetch_module_detail_rows(connection, module_id)
    except Exception as exception:
        raise DatabaseConnectionError("モジュール詳細の取得に失敗しました。") from exception

    return _map_module_detail_rows(rows)


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
            normalized_device_headers = _normalize_device_headers(payload)
            primary_device_header = normalized_device_headers[0]
            device_slot_nos = {header.slot_no for header in normalized_device_headers}

            with connection.cursor() as cursor:
                normalized_module_key = _normalize_module_key(payload.module_key)
                if normalized_module_key is None:
                    normalized_module_key = _generate_next_module_key(cursor)
                else:
                    cursor.execute(
                        "SELECT 1 FROM proc.modules WHERE module_key = %(module_key)s;",
                        {"module_key": normalized_module_key},
                    )
                    if cursor.fetchone() is not None:
                        raise ValueError("module_key already exists.")

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
                        1,
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

            detail_rows = _fetch_module_detail_rows(connection, module_id)
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
