"""Database access helpers for module resources."""

from datetime import date, datetime
from typing import Any

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import ModuleDetailData, ModuleListData, ModuleListItemData, ModuleRowData


MODULE_STATUS_LABELS = {
    "draft": "作成中",
    "published": "承認済み",
    "archived": "保管済み",
}
VALID_MODULE_STATUSES = frozenset(MODULE_STATUS_LABELS)


def _format_updated_at(value: Any) -> str:
    """Format DB updated_at value for API responses.

    Args:
        value: Value returned from PostgreSQL.

    Returns:
        Date string suitable for list displays.
    """

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _build_module_list_query(
    keyword: str | None,
    status_filter: str | None,
) -> tuple[str, dict[str, str]]:
    """Build the module list query and parameters.

    Args:
        keyword: Optional search keyword.
        status_filter: Optional module version status.

    Returns:
        SQL query and named parameters.
    """

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


def list_modules(
    settings: AppSettings,
    keyword: str | None = None,
    status_filter: str | None = None,
) -> ModuleListData:
    """Read modules from PostgreSQL.

    Args:
        settings: Application settings that contain PostgreSQL connection values.
        keyword: Optional search keyword.
        status_filter: Optional status filter. Use ``all`` to disable filtering.

    Returns:
        Module list payload.

    Raises:
        DatabaseConnectionError: If the PostgreSQL driver is missing or the
            module query fails.
    """

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
    """Read the latest module version and rows from PostgreSQL.

    Args:
        settings: Application settings that contain PostgreSQL connection values.
        module_id: Target module identifier.

    Returns:
        Module detail payload when found. ``None`` when the module has no
        version data or does not exist.

    Raises:
        DatabaseConnectionError: If the PostgreSQL driver is missing or the
            module detail query fails.
    """

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    query = """
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
            r.work_text,
            r.check_text_default,
            r.tech_doc_text
        FROM proc.modules m
        JOIN selected_version sv
            ON sv.module_id = m.module_id
        LEFT JOIN proc.module_rows r
            ON r.module_version_id = sv.module_version_id
        WHERE m.module_id = %(module_id)s
        ORDER BY r.row_order;
    """

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, {"module_id": str(module_id)})
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Module detail query failed.") from exception

    if not rows:
        return None

    first_row = rows[0]
    module_rows = [
        ModuleRowData(
            module_row_id=row[11],
            row_order=row[12],
            row_type=row[13],
            work_text=row[14],
            expected_result=row[15],
            note=row[16],
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
