"""Database access helpers for source document resources."""

from datetime import date, datetime
from typing import Any

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ModuleRowData,
    SourceDocDetailData,
    SourceDocListData,
    SourceDocListItemData,
    SourceDocModuleItemData,
)
from app.db.modules import MODULE_STATUS_LABELS


SOURCE_DOC_STATUS_LABELS = {
    "draft": "作成中",
    "published": "承認済み",
    "archived": "保管済み",
}
VALID_SOURCE_DOC_STATUSES = frozenset(SOURCE_DOC_STATUS_LABELS)


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
            bv.status,
            bv.created_by,
            bv.updated_at
        ORDER BY b.blueprint_key, bv.version_no;
    """
    return query, parameters


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
                cursor.execute(query, parameters)
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Source document list query failed.") from exception

    items = [
        SourceDocListItemData(
            source_doc_id=row[0],
            source_doc_key=row[1],
            source_doc_name=row[2],
            description=row[3],
            source_doc_version_id=row[4],
            version_no=row[5],
            status=row[6],
            status_label=SOURCE_DOC_STATUS_LABELS.get(row[6], row[6]),
            module_count=row[7],
            enabled_module_count=row[8],
            module_names=list(row[9] or []),
            created_by=row[10],
            updated_at=_format_updated_at(row[11]),
        )
        for row in rows
    ]

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

    query = """
        WITH selected_version AS (
            SELECT
                bv.blueprint_version_id,
                bv.blueprint_id,
                bv.version_no,
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

    module_rows_query = """
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
            r.check_text_default,
            r.time_text,
            r.window_template_default,
            r.p_template_default,
            r.command_template_default
        FROM selected_version sv
        JOIN proc.blueprint_items bi
            ON bi.blueprint_version_id = sv.blueprint_version_id
        JOIN proc.module_rows r
            ON r.module_version_id = bi.module_version_id
        ORDER BY bi.item_order, r.row_order;
    """

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, {"source_doc_id": str(source_doc_id)})
                rows = cursor.fetchall()
                cursor.execute(module_rows_query, {"source_doc_id": str(source_doc_id)})
                module_row_rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Source document detail query failed.") from exception

    if not rows:
        return None

    first_row = rows[0]
    rows_by_blueprint_item_id: dict[int, list[ModuleRowData]] = {}

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
                expected_result=row[9],
                time_text=row[10],
                window_text=row[11],
                p_text=row[12],
                command_text=row[13],
                note=row[7],
            )
        )

    items = [
        SourceDocModuleItemData(
            blueprint_item_id=row[11],
            item_order=row[12],
            enabled=row[13],
            module_id=row[14],
            module_key=row[15],
            module_name=row[16],
            module_version_id=row[17],
            module_version_no=row[18],
            module_status=row[19],
            module_status_label=MODULE_STATUS_LABELS.get(row[19], row[19]),
            rows=rows_by_blueprint_item_id.get(row[11], []),
        )
        for row in rows
        if row[11] is not None
    ]

    enabled_module_count = sum(1 for item in items if item.enabled)

    return SourceDocDetailData(
        source_doc_id=first_row[0],
        source_doc_key=first_row[1],
        source_doc_name=first_row[2],
        description=first_row[3],
        source_doc_version_id=first_row[4],
        version_no=first_row[5],
        status=first_row[6],
        status_label=SOURCE_DOC_STATUS_LABELS.get(first_row[6], first_row[6]),
        change_note=first_row[7],
        module_count=len(items),
        enabled_module_count=enabled_module_count,
        created_by=first_row[8],
        created_at=_format_updated_at(first_row[9]),
        updated_at=_format_updated_at(first_row[10]),
        items=items,
    )
