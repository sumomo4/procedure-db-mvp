"""Database access helpers for module resources."""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ModuleCreateRequest,
    ModuleDetailData,
    ModuleListData,
    ModuleListItemData,
    ModuleRowData,
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
            r.command_template_default
        FROM proc.modules m
        JOIN selected_version sv
            ON sv.module_id = m.module_id
        LEFT JOIN proc.module_rows r
            ON r.module_version_id = sv.module_version_id
        WHERE m.module_id = %(module_id)s
        ORDER BY r.row_order;
    """


def _fetch_module_detail_rows(connection: Any, module_id: int) -> list[tuple[Any, ...]]:
    """Fetch raw rows used to build a module detail payload."""

    with connection.cursor() as cursor:
        cursor.execute(_build_module_detail_query(), {"module_id": str(module_id)})
        return cursor.fetchall()


def _map_module_detail_rows(rows: Sequence[tuple[Any, ...]]) -> ModuleDetailData | None:
    """Convert raw module detail rows to response data."""

    if not rows:
        return None

    first_row = rows[0]
    module_rows = [
        ModuleRowData(
            module_row_id=row[11],
            row_order=row[12],
            row_type=row[13],
            major_no=row[14],
            middle_no=row[15],
            minor_no=row[16],
            tech_doc_text=row[17],
            work_text=row[18],
            indent_level=row[19],
            expected_result=row[20],
            time_text=row[21],
            window_text=row[22],
            p_text=row[23],
            command_text=row[24],
            note=row[17],
        )
        for row in rows
        if row[11] is not None
    ]

    return ModuleDetailData(
        module_id=first_row[0],
        module_key=first_row[1],
        module_name=first_row[2],
        description=first_row[3],
        module_version_id=first_row[4],
        version_no=first_row[5],
        status=first_row[6],
        status_label=MODULE_STATUS_LABELS.get(first_row[6], first_row[6]),
        row_count=len(module_rows),
        source_xlsx_path=first_row[7],
        created_by=first_row[8],
        created_at=_format_updated_at(first_row[9]),
        updated_at=_format_updated_at(first_row[10]),
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
        raise DatabaseConnectionError("Module detail query failed.") from exception

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
                        created_by
                    )
                    VALUES (
                        %(module_id)s,
                        1,
                        'draft',
                        %(change_note)s,
                        %(source_xlsx_path)s,
                        %(source_sha256)s,
                        %(created_by)s
                    )
                    RETURNING module_version_id;
                    """,
                    {
                        "module_id": module_id,
                        "change_note": payload.change_note,
                        "source_xlsx_path": payload.source_xlsx_path,
                        "source_sha256": payload.source_sha256,
                        "created_by": payload.created_by,
                    },
                )
                inserted_version = cursor.fetchone()
                if inserted_version is None:
                    raise DatabaseConnectionError("Module create failed.")
                module_version_id = int(inserted_version[0])

                for row in sorted(payload.rows, key=lambda item: item.row_order):
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
                            command_template_default
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
                            %(command_text)s
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
                            "time_text": row.time_text,
                            "window_text": row.window_text,
                            "p_text": row.p_text,
                            "command_text": row.command_text,
                        },
                    )
                    cursor.fetchone()

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
