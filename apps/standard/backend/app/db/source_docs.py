"""Database access helpers for source document resources."""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    SourceDocCreateRequest,
    SourceDocUpdateRequest,
    ModuleRowData,
    SourceDocDetailData,
    SourceDocListData,
    SourceDocListItemData,
    SourceDocModuleItemData,
)
from app.db.modules import MODULE_STATUS_LABELS, _map_device_entries, _map_row_images


SOURCE_DOC_STATUS_LABELS = {
    "draft": "作成中",
    "review_requested": "承認依頼中",
    "returned": "差戻し",
    "published": "承認済み",
    "archived": "保管済み",
}
VALID_SOURCE_DOC_STATUSES = frozenset(SOURCE_DOC_STATUS_LABELS)


def _format_source_doc_version_label(version_major: int | None, version_minor: int | None) -> str:
    """Format a user-facing source document version label."""

    major = max(int(version_major or 0), 0)
    minor = max(int(version_minor or 0), 0)
    return f"ver.{major}.{minor}"


def _derive_source_doc_version_tuple(
    version_no: int | None,
    status: str | None,
    version_major: Any = None,
    version_minor: Any = None,
) -> tuple[int, int]:
    """Derive display version values for old rows that predate version columns."""

    try:
        if version_major is not None and version_minor is not None:
            return (max(int(version_major), 0), max(int(version_minor), 0))
    except (TypeError, ValueError):
        pass

    sequence_no = int(version_no or 1)
    if status in ("published", "archived"):
        return (sequence_no, 0)
    if status in ("review_requested", "returned"):
        return (max(sequence_no - 1, 0), 1)
    return (max(sequence_no - 1, 0), 0)


def _ensure_source_doc_version_number_columns(cursor: Any) -> None:
    """Ensure user-facing ver.X.Y columns exist on existing DB volumes."""

    cursor.execute(
        """
        ALTER TABLE proc.blueprint_versions
            ADD COLUMN IF NOT EXISTS version_major integer NOT NULL DEFAULT 0;
        ALTER TABLE proc.blueprint_versions
            ADD COLUMN IF NOT EXISTS version_minor integer NOT NULL DEFAULT 0;
        """,
        {},
    )
    cursor.execute(
        """
        UPDATE proc.blueprint_versions
        SET
            version_major = CASE
                WHEN status IN ('published', 'archived') THEN version_no
                ELSE GREATEST(version_no - 1, 0)
            END,
            version_minor = CASE
                WHEN status IN ('review_requested', 'returned') THEN 1
                ELSE 0
            END
        WHERE version_major = 0
          AND version_minor = 0
          AND version_no > 0;
        """,
        {},
    )


def _latest_source_doc_display_version(cursor: Any, source_doc_id: int) -> tuple[int, int]:
    """Read the latest display version tuple for a source document."""

    cursor.execute(
        """
        SELECT version_major, version_minor
        FROM proc.blueprint_versions
        WHERE blueprint_id = %(source_doc_id)s
        ORDER BY version_no DESC
        LIMIT 1;
        """,
        {"source_doc_id": source_doc_id},
    )
    row = cursor.fetchone()
    if row is None:
        return (0, 0)
    return (max(int(row[0] or 0), 0), max(int(row[1] or 0), 0))


def _format_updated_at(value: Any) -> str:
    """Format DB timestamp/date values for API responses."""

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _build_source_doc_list_query(
    keyword: str | None,
    status_filter: str | None,
) -> tuple[str, dict[str, str]]:
    """Build the source document list query and parameters."""

    conditions: list[str] = []
    parameters: dict[str, str] = {}

    if keyword:
        conditions.append(
            """
            (
                b.blueprint_key ILIKE %(keyword)s
                OR b.name ILIKE %(keyword)s
                OR COALESCE(b.description, '') ILIKE %(keyword)s
                OR EXISTS (
                    SELECT 1
                    FROM proc.blueprint_items bix
                    JOIN proc.module_versions mvx
                        ON mvx.module_version_id = bix.module_version_id
                    JOIN proc.modules mx
                        ON mx.module_id = mvx.module_id
                    WHERE bix.blueprint_version_id = bv.blueprint_version_id
                      AND (
                          mx.module_key ILIKE %(keyword)s
                          OR mx.name ILIKE %(keyword)s
                      )
                )
            )
            """
        )
        parameters["keyword"] = f"%{keyword}%"

    if status_filter and status_filter != "all":
        conditions.append("bv.status = %(status_filter)s")
        parameters["status_filter"] = status_filter

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT
            b.blueprint_id,
            b.blueprint_key,
            b.name AS source_doc_name,
            b.description,
            bv.blueprint_version_id,
            bv.version_no,
            bv.version_major,
            bv.version_minor,
            bv.status,
            COUNT(bi.blueprint_item_id)::int AS module_count,
            COUNT(*) FILTER (WHERE COALESCE(bi.enabled, false))::int AS enabled_module_count,
            COALESCE(
                ARRAY_AGG(m.name ORDER BY bi.item_order)
                    FILTER (WHERE bi.blueprint_item_id IS NOT NULL),
                ARRAY[]::text[]
            ) AS module_names,
            bv.created_by,
            bv.updated_at
        FROM proc.blueprints b
        JOIN proc.blueprint_versions bv
            ON bv.blueprint_id = b.blueprint_id
        LEFT JOIN proc.blueprint_items bi
            ON bi.blueprint_version_id = bv.blueprint_version_id
        LEFT JOIN proc.module_versions mv
            ON mv.module_version_id = bi.module_version_id
        LEFT JOIN proc.modules m
            ON m.module_id = mv.module_id
        {where_clause}
        GROUP BY
            b.blueprint_id,
            b.blueprint_key,
            b.name,
            b.description,
            bv.blueprint_version_id,
            bv.version_no,
            bv.version_major,
            bv.version_minor,
            bv.status,
            bv.created_by,
            bv.updated_at
        ORDER BY b.blueprint_key, bv.version_no;
    """
    return query, parameters


def _build_source_doc_detail_query() -> str:
    """Build the source document detail query."""

    return """
        WITH selected_version AS (
            SELECT
            bv.blueprint_version_id,
            bv.blueprint_id,
            bv.version_no,
            bv.version_major,
            bv.version_minor,
            bv.status,
                bv.change_note,
                bv.created_by,
                bv.created_at,
                bv.updated_at
            FROM proc.blueprint_versions bv
            WHERE bv.blueprint_id = %(source_doc_id)s
            ORDER BY bv.version_no DESC
            LIMIT 1
        )
        SELECT
            b.blueprint_id,
            b.blueprint_key,
            b.name AS source_doc_name,
            b.description,
            sv.blueprint_version_id,
            sv.version_no,
            sv.version_major,
            sv.version_minor,
            sv.status,
            sv.change_note,
            sv.created_by,
            sv.created_at,
            sv.updated_at,
            bi.blueprint_item_id,
            bi.item_order,
            bi.enabled,
            m.module_id,
            m.module_key,
            m.name AS module_name,
            mv.module_version_id,
            mv.version_no AS module_version_no,
            mv.status AS module_status
        FROM proc.blueprints b
        JOIN selected_version sv
            ON sv.blueprint_id = b.blueprint_id
        LEFT JOIN proc.blueprint_items bi
            ON bi.blueprint_version_id = sv.blueprint_version_id
        LEFT JOIN proc.module_versions mv
            ON mv.module_version_id = bi.module_version_id
        LEFT JOIN proc.modules m
            ON m.module_id = mv.module_id
        WHERE b.blueprint_id = %(source_doc_id)s
        ORDER BY bi.item_order;
    """


def _build_source_doc_module_rows_query() -> str:
    """Build the source document module rows query."""

    return """
        WITH selected_version AS (
            SELECT
                bv.blueprint_version_id
            FROM proc.blueprint_versions bv
            WHERE bv.blueprint_id = %(source_doc_id)s
            ORDER BY bv.version_no DESC
            LIMIT 1
        )
        SELECT
            bi.blueprint_item_id,
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
        FROM selected_version sv
        JOIN proc.blueprint_items bi
            ON bi.blueprint_version_id = sv.blueprint_version_id
        JOIN proc.module_rows r
            ON r.module_version_id = bi.module_version_id
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
        ORDER BY bi.item_order, r.row_order;
    """


def _fetch_source_doc_detail_rows(
    connection: Any,
    source_doc_id: int,
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    """Fetch raw rows used to build a source document detail payload."""

    with connection.cursor() as cursor:
        _ensure_source_doc_version_number_columns(cursor)
        cursor.execute(_build_source_doc_detail_query(), {"source_doc_id": str(source_doc_id)})
        rows = cursor.fetchall()
        cursor.execute(_build_source_doc_module_rows_query(), {"source_doc_id": str(source_doc_id)})
        module_row_rows = cursor.fetchall()
    return rows, module_row_rows


def _map_source_doc_detail_rows(
    rows: Sequence[tuple[Any, ...]],
    module_row_rows: Sequence[tuple[Any, ...]],
) -> SourceDocDetailData | None:
    """Convert raw source document detail rows to response data."""

    if not rows:
        return None

    first_row = rows[0]
    rows_by_blueprint_item_id: dict[int, list[ModuleRowData]] = {}
    has_version_columns = len(first_row) >= 22
    item_base_index = 13 if has_version_columns else 11

    for row in module_row_rows:
        blueprint_item_id = row[0]
        rows_by_blueprint_item_id.setdefault(blueprint_item_id, []).append(
            ModuleRowData(
                module_row_id=row[1],
                row_order=row[2],
                row_type=row[3],
                major_no=row[4],
                middle_no=row[5],
                minor_no=row[6],
                tech_doc_text=row[7],
                work_text=row[8],
                indent_level=row[9],
                expected_result=row[10],
                time_text=row[11],
                window_text=row[12],
                p_text=row[13],
                command_text=row[14],
                note=row[7],
                device_entries=_map_device_entries(
                    row[15] if len(row) > 15 else None,
                    row[11],
                    row[12],
                    row[13],
                    row[14],
                ),
                images=_map_row_images(row[16] if len(row) > 16 else None),
            )
        )

    items = [
        SourceDocModuleItemData(
            blueprint_item_id=row[item_base_index],
            item_order=row[item_base_index + 1],
            enabled=row[item_base_index + 2],
            module_id=row[item_base_index + 3],
            module_key=row[item_base_index + 4],
            module_name=row[item_base_index + 5],
            module_version_id=row[item_base_index + 6],
            module_version_no=row[item_base_index + 7],
            module_status=row[item_base_index + 8],
            module_status_label=MODULE_STATUS_LABELS.get(row[item_base_index + 8], row[item_base_index + 8]),
            rows=rows_by_blueprint_item_id.get(row[item_base_index], []),
        )
        for row in rows
        if row[item_base_index] is not None
    ]

    enabled_module_count = sum(1 for item in items if item.enabled)

    version_major, version_minor = _derive_source_doc_version_tuple(
        first_row[5],
        first_row[8] if has_version_columns else first_row[6],
        first_row[6] if has_version_columns else None,
        first_row[7] if has_version_columns else None,
    )
    status_index = 8 if has_version_columns else 6
    change_note_index = 9 if has_version_columns else 7
    created_by_index = 10 if has_version_columns else 8
    created_at_index = 11 if has_version_columns else 9
    updated_at_index = 12 if has_version_columns else 10

    return SourceDocDetailData(
        source_doc_id=first_row[0],
        source_doc_key=first_row[1],
        source_doc_name=first_row[2],
        description=first_row[3],
        source_doc_version_id=first_row[4],
        version_no=first_row[5],
        version_major=version_major,
        version_minor=version_minor,
        version_label=_format_source_doc_version_label(version_major, version_minor),
        status=first_row[status_index],
        status_label=SOURCE_DOC_STATUS_LABELS.get(first_row[status_index], first_row[status_index]),
        change_note=first_row[change_note_index],
        module_count=len(items),
        enabled_module_count=enabled_module_count,
        created_by=first_row[created_by_index],
        created_at=_format_updated_at(first_row[created_at_index]),
        updated_at=_format_updated_at(first_row[updated_at_index]),
        items=items,
    )


def _normalize_source_doc_key(source_doc_key: str | None) -> str | None:
    """Normalize source document key text."""

    if source_doc_key is None:
        return None

    normalized_key = source_doc_key.strip().upper()
    if not normalized_key:
        raise ValueError("source_doc_key must not be blank.")
    return normalized_key


def _validate_source_doc_write_request(
    payload: SourceDocCreateRequest | SourceDocUpdateRequest,
) -> None:
    """Validate create/update payload with business rules."""

    if not payload.source_doc_name.strip():
        raise ValueError("source_doc_name must not be blank.")

    module_ids = [item.module_id for item in payload.items]
    if len(module_ids) != len(set(module_ids)):
        raise ValueError("module_id must be unique within items.")

    item_orders = [item.item_order for item in payload.items if item.item_order is not None]
    if len(item_orders) != len(set(item_orders)):
        raise ValueError("item_order must be unique within items.")


def _generate_next_source_doc_key(cursor: Any) -> str:
    """Generate the next sequential source document key."""

    cursor.execute(
        """
        SELECT COALESCE(
            MAX((regexp_match(blueprint_key, '^BP-STD-(\\d+)$'))[1]::int),
            0
        )
        FROM proc.blueprints
        WHERE blueprint_key ~ '^BP-STD-\\d+$';
        """,
        {},
    )
    row = cursor.fetchone()
    next_no = int(row[0]) + 1 if row and row[0] is not None else 1
    return f"BP-STD-{next_no:03d}"


def _resolve_latest_module_version_id(cursor: Any, module_id: int) -> int:
    """Resolve the latest module version id for the given module."""

    cursor.execute(
        """
        SELECT mv.module_version_id
        FROM proc.module_versions mv
        WHERE mv.module_id = %(module_id)s
        ORDER BY mv.version_no DESC
        LIMIT 1;
        """,
        {"module_id": module_id},
    )
    module_version_row = cursor.fetchone()
    if module_version_row is None:
        raise ValueError(f"module_id {module_id} was not found.")
    return int(module_version_row[0])


def _insert_source_doc_items(
    cursor: Any,
    source_doc_version_id: int,
    items: Sequence[Any],
) -> None:
    """Insert linked module items for a source document version."""

    ordered_items = sorted(
        enumerate(items, start=1),
        key=lambda pair: pair[1].item_order if pair[1].item_order is not None else pair[0],
    )
    for fallback_order, item in ordered_items:
        module_version_id = _resolve_latest_module_version_id(cursor, item.module_id)
        cursor.execute(
            """
            INSERT INTO proc.blueprint_items (
                blueprint_version_id,
                item_order,
                module_version_id,
                enabled
            )
            VALUES (
                %(source_doc_version_id)s,
                %(item_order)s,
                %(module_version_id)s,
                %(enabled)s
            )
            RETURNING blueprint_item_id;
            """,
            {
                "source_doc_version_id": source_doc_version_id,
                "item_order": item.item_order if item.item_order is not None else fallback_order,
                "module_version_id": module_version_id,
                "enabled": item.enabled,
            },
        )
        cursor.fetchone()


def list_source_docs(
    settings: AppSettings,
    keyword: str | None = None,
    status_filter: str | None = None,
) -> SourceDocListData:
    """Read source document list from PostgreSQL."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    query, parameters = _build_source_doc_list_query(keyword, status_filter)

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                _ensure_source_doc_version_number_columns(cursor)
                cursor.execute(query, parameters)
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Source document list query failed.") from exception

    items = []
    for row in rows:
        has_version_columns = len(row) >= 14
        status_index = 8 if has_version_columns else 6
        module_count_index = 9 if has_version_columns else 7
        enabled_count_index = 10 if has_version_columns else 8
        module_names_index = 11 if has_version_columns else 9
        created_by_index = 12 if has_version_columns else 10
        updated_at_index = 13 if has_version_columns else 11
        version_major, version_minor = _derive_source_doc_version_tuple(
            row[5],
            row[status_index],
            row[6] if has_version_columns else None,
            row[7] if has_version_columns else None,
        )
        items.append(
            SourceDocListItemData(
                source_doc_id=row[0],
                source_doc_key=row[1],
                source_doc_name=row[2],
                description=row[3],
                source_doc_version_id=row[4],
                version_no=row[5],
                version_major=version_major,
                version_minor=version_minor,
                version_label=_format_source_doc_version_label(version_major, version_minor),
                status=row[status_index],
                status_label=SOURCE_DOC_STATUS_LABELS.get(row[status_index], row[status_index]),
                module_count=row[module_count_index],
                enabled_module_count=row[enabled_count_index],
                module_names=list(row[module_names_index] or []),
                created_by=row[created_by_index],
                updated_at=_format_updated_at(row[updated_at_index]),
            )
        )

    return SourceDocListData(items=items)


def get_source_doc_detail(
    settings: AppSettings,
    source_doc_id: int,
) -> SourceDocDetailData | None:
    """Read the latest source document version and linked modules from PostgreSQL."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            rows, module_row_rows = _fetch_source_doc_detail_rows(connection, source_doc_id)
    except Exception as exception:
        raise DatabaseConnectionError("Source document detail query failed.") from exception

    return _map_source_doc_detail_rows(rows, module_row_rows)


def create_source_doc(
    settings: AppSettings,
    payload: SourceDocCreateRequest,
) -> SourceDocDetailData:
    """Create a source document, its initial version, and linked modules."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    _validate_source_doc_write_request(payload)

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            source_doc_id: int | None = None

            with connection.cursor() as cursor:
                _ensure_source_doc_version_number_columns(cursor)
                normalized_source_doc_key = _normalize_source_doc_key(payload.source_doc_key)
                if normalized_source_doc_key is None:
                    normalized_source_doc_key = _generate_next_source_doc_key(cursor)
                else:
                    cursor.execute(
                        "SELECT 1 FROM proc.blueprints WHERE blueprint_key = %(source_doc_key)s;",
                        {"source_doc_key": normalized_source_doc_key},
                    )
                    if cursor.fetchone() is not None:
                        raise ValueError("source_doc_key already exists.")

                cursor.execute(
                    """
                    INSERT INTO proc.blueprints (blueprint_key, name, description)
                    VALUES (%(source_doc_key)s, %(source_doc_name)s, %(description)s)
                    RETURNING blueprint_id;
                    """,
                    {
                        "source_doc_key": normalized_source_doc_key,
                        "source_doc_name": payload.source_doc_name.strip(),
                        "description": payload.description,
                    },
                )
                inserted_source_doc = cursor.fetchone()
                if inserted_source_doc is None:
                    raise DatabaseConnectionError("Source document create failed.")
                source_doc_id = int(inserted_source_doc[0])

                cursor.execute(
                    """
                    INSERT INTO proc.blueprint_versions (
                        blueprint_id,
                        version_no,
                        version_major,
                        version_minor,
                        status,
                        change_note,
                        created_by
                    )
                    VALUES (
                        %(source_doc_id)s,
                        1,
                        0,
                        0,
                        'draft',
                        %(change_note)s,
                        %(created_by)s
                    )
                    RETURNING blueprint_version_id;
                    """,
                    {
                        "source_doc_id": source_doc_id,
                        "change_note": payload.change_note,
                        "created_by": payload.created_by,
                    },
                )
                inserted_version = cursor.fetchone()
                if inserted_version is None:
                    raise DatabaseConnectionError("Source document create failed.")
                source_doc_version_id = int(inserted_version[0])

                _insert_source_doc_items(cursor, source_doc_version_id, payload.items)

            if source_doc_id is None:
                raise DatabaseConnectionError("Source document create failed.")

            detail_rows, module_row_rows = _fetch_source_doc_detail_rows(connection, source_doc_id)
            connection.commit()
    except ValueError:
        raise
    except DatabaseConnectionError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("Source document create failed.") from exception

    detail = _map_source_doc_detail_rows(detail_rows, module_row_rows)
    if detail is None:
        raise DatabaseConnectionError("Source document create failed.")
    return detail


def update_source_doc(
    settings: AppSettings,
    source_doc_id: int,
    payload: SourceDocUpdateRequest,
) -> SourceDocDetailData | None:
    """Update a source document and create its next draft version."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    _validate_source_doc_write_request(payload)

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                _ensure_source_doc_version_number_columns(cursor)
                cursor.execute(
                    """
                    SELECT blueprint_key
                    FROM proc.blueprints
                    WHERE blueprint_id = %(source_doc_id)s;
                    """,
                    {"source_doc_id": source_doc_id},
                )
                existing_source_doc = cursor.fetchone()
                if existing_source_doc is None:
                    return None

                normalized_source_doc_key = _normalize_source_doc_key(payload.source_doc_key)
                if normalized_source_doc_key is None:
                    normalized_source_doc_key = str(existing_source_doc[0])
                else:
                    cursor.execute(
                        """
                        SELECT 1
                        FROM proc.blueprints
                        WHERE blueprint_key = %(source_doc_key)s
                          AND blueprint_id <> %(source_doc_id)s;
                        """,
                        {
                            "source_doc_key": normalized_source_doc_key,
                            "source_doc_id": source_doc_id,
                        },
                    )
                    if cursor.fetchone() is not None:
                        raise ValueError("source_doc_key already exists.")

                cursor.execute(
                    """
                    UPDATE proc.blueprints
                    SET
                        blueprint_key = %(source_doc_key)s,
                        name = %(source_doc_name)s,
                        description = %(description)s
                    WHERE blueprint_id = %(source_doc_id)s;
                    """,
                    {
                        "source_doc_id": source_doc_id,
                        "source_doc_key": normalized_source_doc_key,
                        "source_doc_name": payload.source_doc_name.strip(),
                        "description": payload.description,
                    },
                )

                cursor.execute(
                    """
                    SELECT COALESCE(MAX(version_no), 0) + 1
                    FROM proc.blueprint_versions
                    WHERE blueprint_id = %(source_doc_id)s;
                    """,
                    {"source_doc_id": source_doc_id},
                )
                next_version_row = cursor.fetchone()
                next_version_no = int(next_version_row[0]) if next_version_row and next_version_row[0] is not None else 1
                next_version_major, next_version_minor = _latest_source_doc_display_version(cursor, source_doc_id)

                cursor.execute(
                    """
                    INSERT INTO proc.blueprint_versions (
                        blueprint_id,
                        version_no,
                        version_major,
                        version_minor,
                        status,
                        change_note,
                        created_by
                    )
                    VALUES (
                        %(source_doc_id)s,
                        %(version_no)s,
                        %(version_major)s,
                        %(version_minor)s,
                        'draft',
                        %(change_note)s,
                        %(created_by)s
                    )
                    RETURNING blueprint_version_id;
                    """,
                    {
                        "source_doc_id": source_doc_id,
                        "version_no": next_version_no,
                        "version_major": next_version_major,
                        "version_minor": next_version_minor,
                        "change_note": payload.change_note,
                        "created_by": payload.created_by,
                    },
                )
                inserted_version = cursor.fetchone()
                if inserted_version is None:
                    raise DatabaseConnectionError("Source document update failed.")
                source_doc_version_id = int(inserted_version[0])

                _insert_source_doc_items(cursor, source_doc_version_id, payload.items)

            detail_rows, module_row_rows = _fetch_source_doc_detail_rows(connection, source_doc_id)
            connection.commit()
    except ValueError:
        raise
    except DatabaseConnectionError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("Source document update failed.") from exception

    detail = _map_source_doc_detail_rows(detail_rows, module_row_rows)
    if detail is None:
        raise DatabaseConnectionError("Source document update failed.")
    return detail
