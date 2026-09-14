"""Persistence helpers for executable case document instances."""

from collections.abc import Sequence
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    CaseDocExecutionCommentData,
    CaseDocExecutionCommentUpdateRequest,
    CaseDocExecutionHistoryData,
    CaseDocExecutionItemData,
    CaseDocExecutionBulkUpdateRequest,
    CaseDocExecutionUpdateRequest,
    CaseDocInstanceDetailData,
    CaseDocInstanceListData,
    CaseDocInstanceListItemData,
    CaseDocPreparationData,
    CaseDocPreparationUpdateRequest,
    CaseDocResolveContextData,
    CaseDocTargetDeviceSlotData,
    ModuleRowImageData,
    SourceDocDetailData,
)


CASE_DOC_INSTANCE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS proc.case_documents (
    case_document_id bigserial PRIMARY KEY,
    case_document_key text NOT NULL UNIQUE,
    case_name text,
    source_doc_id bigint NOT NULL,
    source_doc_version_id bigint NOT NULL,
    source_doc_key text NOT NULL,
    source_doc_name text NOT NULL,
    unit_config_id text NOT NULL,
    prefecture text NOT NULL,
    building text NOT NULL,
    context_json jsonb NOT NULL,
    preparation_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    tags_initialized boolean NOT NULL DEFAULT false,
    workbook_path text NOT NULL,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

ALTER TABLE proc.case_documents
    ADD COLUMN IF NOT EXISTS preparation_json jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE proc.case_documents
    ADD COLUMN IF NOT EXISTS case_name text;
ALTER TABLE proc.case_documents
    ADD COLUMN IF NOT EXISTS tags_initialized boolean NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS proc.case_document_tag_memberships (
    case_document_id bigint NOT NULL REFERENCES proc.case_documents (case_document_id) ON DELETE CASCADE,
    tag_path text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (case_document_id, tag_path)
);

CREATE INDEX IF NOT EXISTS idx_case_document_tag_memberships_tag_path
    ON proc.case_document_tag_memberships (tag_path);

CREATE TABLE IF NOT EXISTS proc.case_document_targets (
    case_document_target_id bigserial PRIMARY KEY,
    case_document_id bigint NOT NULL REFERENCES proc.case_documents (case_document_id) ON DELETE CASCADE,
    target_no integer NOT NULL CHECK (target_no BETWEEN 1 AND 20),
    slot_key text NOT NULL,
    device_type text NOT NULL,
    system text,
    host_name text NOT NULL,
    UNIQUE (case_document_id, target_no)
);

CREATE TABLE IF NOT EXISTS proc.case_document_execution_items (
    execution_item_id bigserial PRIMARY KEY,
    case_document_id bigint NOT NULL REFERENCES proc.case_documents (case_document_id) ON DELETE CASCADE,
    module_row_id bigint,
    row_order integer NOT NULL CHECK (row_order > 0),
    target_no integer NOT NULL CHECK (target_no BETWEEN 1 AND 20),
    excel_cell text NOT NULL,
    major_no text,
    middle_no text,
    minor_no text,
    tech_doc_text text,
    work_text text,
    check_text text,
    window_text text,
    p_text text,
    command_text text,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'checked', 'skipped')),
    performed_at timestamptz,
    performed_by text,
    skip_reason text,
    lock_version integer NOT NULL DEFAULT 0 CHECK (lock_version >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_document_id, row_order, target_no)
);

ALTER TABLE proc.case_document_execution_items
    ADD COLUMN IF NOT EXISTS tech_doc_text text;
ALTER TABLE proc.case_document_execution_items
    ADD COLUMN IF NOT EXISTS window_text text;
ALTER TABLE proc.case_document_execution_items
    ADD COLUMN IF NOT EXISTS p_text text;

CREATE INDEX IF NOT EXISTS idx_case_document_execution_items_case_document
    ON proc.case_document_execution_items (case_document_id, row_order, target_no);

CREATE TABLE IF NOT EXISTS proc.case_document_execution_comments (
    execution_comment_id bigserial PRIMARY KEY,
    case_document_id bigint NOT NULL REFERENCES proc.case_documents (case_document_id) ON DELETE CASCADE,
    group_start_row_order integer NOT NULL CHECK (group_start_row_order > 0),
    item_label text NOT NULL,
    comment_text text NOT NULL DEFAULT '',
    updated_by text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    lock_version integer NOT NULL DEFAULT 0 CHECK (lock_version >= 0),
    UNIQUE (case_document_id, group_start_row_order)
);

CREATE TABLE IF NOT EXISTS proc.case_document_execution_histories (
    history_id bigserial PRIMARY KEY,
    execution_item_id bigint NOT NULL REFERENCES proc.case_document_execution_items (execution_item_id) ON DELETE CASCADE,
    from_status text NOT NULL CHECK (from_status IN ('pending', 'checked', 'skipped')),
    to_status text NOT NULL CHECK (to_status IN ('pending', 'checked', 'skipped')),
    changed_at timestamptz NOT NULL DEFAULT now(),
    changed_by text,
    note text
);

CREATE INDEX IF NOT EXISTS idx_case_document_execution_histories_item
    ON proc.case_document_execution_histories (execution_item_id, changed_at);
"""


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _normalize_case_doc_tag_paths(tag_paths: Sequence[str] | None) -> list[str]:
    """Normalize inherited tag paths while preserving letter case."""

    if isinstance(tag_paths, str):
        tag_paths = [tag_paths]
    normalized: list[str] = []
    for tag_path in tag_paths or []:
        value = "/".join(
            part.strip()
            for part in str(tag_path).strip().replace("\\", "/").split("/")
            if part.strip()
        )
        value = value or "未分類"
        if value not in normalized:
            normalized.append(value)
    return normalized or ["未分類"]


def _ensure_schema(cursor: Any) -> None:
    cursor.execute(CASE_DOC_INSTANCE_SCHEMA_SQL)
    cursor.execute("SELECT to_regclass('proc.blueprint_tag_memberships') AS relation_name;")
    source_tag_table = cursor.fetchone()
    if source_tag_table and source_tag_table["relation_name"] is not None:
        cursor.execute(
            """
            INSERT INTO proc.case_document_tag_memberships (case_document_id, tag_path)
            SELECT cd.case_document_id, source_tag.tag_path
            FROM proc.case_documents cd
            JOIN proc.blueprint_tag_memberships source_tag
              ON source_tag.blueprint_id = cd.source_doc_id
            WHERE cd.tags_initialized = false
              AND NOT EXISTS (
                SELECT 1
                FROM proc.case_document_tag_memberships existing_tag
                WHERE existing_tag.case_document_id = cd.case_document_id
            )
            ON CONFLICT (case_document_id, tag_path) DO NOTHING;
            """
        )
    cursor.execute(
        """
        INSERT INTO proc.case_document_tag_memberships (case_document_id, tag_path)
        SELECT cd.case_document_id, '未分類'
        FROM proc.case_documents cd
        WHERE cd.tags_initialized = false
          AND NOT EXISTS (
            SELECT 1
            FROM proc.case_document_tag_memberships existing_tag
            WHERE existing_tag.case_document_id = cd.case_document_id
        )
        ON CONFLICT (case_document_id, tag_path) DO NOTHING;
        """
    )
    cursor.execute(
        """
        UPDATE proc.case_documents
        SET tags_initialized = true
        WHERE tags_initialized = false;
        """
    )


def _write_original_workbook(settings: AppSettings, case_document_key: str, workbook_bytes: bytes) -> Path:
    storage_dir = Path(settings.case_doc_instance_storage_dir)
    instance_dir = storage_dir / case_document_key
    instance_dir.mkdir(parents=True, exist_ok=True)
    workbook_path = instance_dir / "original.xlsm"
    temporary_path = instance_dir / "original.xlsm.tmp"
    temporary_path.write_bytes(workbook_bytes)
    temporary_path.replace(workbook_path)
    return workbook_path


def _summary_from_row(row: dict[str, Any]) -> CaseDocInstanceListItemData:
    return CaseDocInstanceListItemData(
        case_document_id=row["case_document_id"],
        case_document_key=row["case_document_key"],
        case_name=str(row.get("case_name") or row.get("source_doc_name") or "").strip(),
        tag_paths=_normalize_case_doc_tag_paths(row.get("tag_paths")),
        source_doc_id=row["source_doc_id"],
        source_doc_key=row["source_doc_key"],
        source_doc_name=row["source_doc_name"],
        unit_config_id=row["unit_config_id"],
        status=row["status"],
        total_count=row["total_count"],
        checked_count=row["checked_count"],
        skipped_count=row["skipped_count"],
        pending_count=row["pending_count"],
        resume_item_label=str(row.get("resume_item_label") or "").strip() or None,
        created_by=row["created_by"],
        created_at=_isoformat(row["created_at"]) or "",
        updated_at=_isoformat(row["updated_at"]) or "",
    )


def _preparation_from_row(row: dict[str, Any]) -> CaseDocPreparationData:
    """Return preparation data with the original unit configuration as fallback."""

    raw_preparation = row.get("preparation_json")
    if not isinstance(raw_preparation, dict):
        raw_preparation = {}
    raw_context = row.get("context_json")
    if not isinstance(raw_context, dict):
        raw_context = {}
    raw_unit_config = raw_context.get("unit_config")
    if not isinstance(raw_unit_config, dict):
        raw_unit_config = {}

    return CaseDocPreparationData(
        construction_name=str(raw_preparation.get("construction_name") or ""),
        construction_date=raw_preparation.get("construction_date"),
        construction_executor=str(raw_preparation.get("construction_executor") or ""),
        block=str(raw_preparation.get("block") or raw_unit_config.get("block") or ""),
        target_fs=str(raw_preparation.get("target_fs") or raw_unit_config.get("fs_cluster_name") or ""),
        updated_by=raw_preparation.get("updated_by"),
        updated_at=_isoformat(raw_preparation.get("updated_at")),
    )


def _is_preparation_complete(raw_preparation: Any) -> bool:
    """Return whether all values required before execution have been saved."""

    if not isinstance(raw_preparation, dict):
        return False
    required_fields = (
        "construction_name",
        "construction_date",
        "construction_executor",
        "block",
        "target_fs",
        "updated_at",
    )
    return all(str(raw_preparation.get(field) or "").strip() for field in required_fields)


CASE_DOC_SUMMARY_SELECT = """
SELECT
    cd.case_document_id,
    cd.case_document_key,
    COALESCE(
        NULLIF(BTRIM(cd.case_name), ''),
        NULLIF(BTRIM(cd.preparation_json ->> 'construction_name'), ''),
        cd.source_doc_name
    ) AS case_name,
    COALESCE(
        (
            SELECT array_agg(case_tag.tag_path ORDER BY case_tag.tag_path)
            FROM proc.case_document_tag_memberships case_tag
            WHERE case_tag.case_document_id = cd.case_document_id
        ),
        ARRAY['未分類']::text[]
    ) AS tag_paths,
    cd.source_doc_id,
    cd.source_doc_key,
    cd.source_doc_name,
    cd.unit_config_id,
    cd.status,
    COUNT(cei.execution_item_id)::integer AS total_count,
    COUNT(*) FILTER (WHERE cei.status = 'checked')::integer AS checked_count,
    COUNT(*) FILTER (WHERE cei.status = 'skipped')::integer AS skipped_count,
    COUNT(*) FILTER (WHERE cei.status = 'pending')::integer AS pending_count,
    (
        SELECT COALESCE(
            NULLIF(
                CONCAT_WS(
                    '.',
                    NULLIF(BTRIM(next_item.major_no), ''),
                    NULLIF(BTRIM(next_item.middle_no), ''),
                    NULLIF(BTRIM(next_item.minor_no), '')
                ),
                ''
            ),
            (
                SELECT NULLIF(
                    CONCAT_WS(
                        '.',
                        NULLIF(BTRIM(group_start.major_no), ''),
                        NULLIF(BTRIM(group_start.middle_no), ''),
                        NULLIF(BTRIM(group_start.minor_no), '')
                    ),
                    ''
                )
                FROM proc.case_document_execution_items group_start
                WHERE group_start.case_document_id = cd.case_document_id
                  AND group_start.row_order <= next_item.row_order
                  AND NULLIF(BTRIM(group_start.minor_no), '') IS NOT NULL
                ORDER BY group_start.row_order DESC, group_start.target_no
                LIMIT 1
            ),
            '番号なし'
        )
        FROM proc.case_document_execution_items next_item
        WHERE next_item.case_document_id = cd.case_document_id
          AND next_item.status = 'pending'
        ORDER BY next_item.row_order, next_item.target_no
        LIMIT 1
    ) AS resume_item_label,
    cd.created_by,
    cd.created_at,
    cd.updated_at,
    cd.prefecture,
    cd.building,
    cd.context_json,
    cd.preparation_json,
    cd.workbook_path
FROM proc.case_documents cd
LEFT JOIN proc.case_document_execution_items cei
    ON cei.case_document_id = cd.case_document_id
"""


CASE_DOC_SUMMARY_GROUP = """
GROUP BY
    cd.case_document_id,
    cd.case_document_key,
    cd.case_name,
    cd.source_doc_id,
    cd.source_doc_key,
    cd.source_doc_name,
    cd.unit_config_id,
    cd.status,
    cd.created_by,
    cd.created_at,
    cd.updated_at,
    cd.prefecture,
    cd.building,
    cd.context_json,
    cd.preparation_json,
    cd.workbook_path
"""


VALID_CASE_DOC_EXECUTION_STATUSES = frozenset({"all", "active", "not_started", "in_progress", "completed"})


def _build_case_doc_list_filter(
    keyword: str | None,
    tag_paths: Sequence[str] | None,
    execution_status: str | None,
) -> tuple[str, dict[str, object]]:
    """Build server-side filters for the executable case document list."""

    conditions: list[str] = []
    parameters: dict[str, object] = {}
    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        conditions.append(
            """
            (
                cd.case_document_key ILIKE %(keyword)s
                OR COALESCE(cd.case_name, '') ILIKE %(keyword)s
                OR cd.source_doc_key ILIKE %(keyword)s
                OR cd.source_doc_name ILIKE %(keyword)s
                OR COALESCE(cd.preparation_json ->> 'construction_name', '') ILIKE %(keyword)s
                OR EXISTS (
                    SELECT 1
                    FROM proc.case_document_tag_memberships keyword_tag
                    WHERE keyword_tag.case_document_id = cd.case_document_id
                      AND keyword_tag.tag_path ILIKE %(keyword)s
                )
            )
            """
        )
        parameters["keyword"] = f"%{normalized_keyword}%"

    for index, tag_path in enumerate(_normalize_case_doc_tag_paths(tag_paths) if tag_paths else []):
        parameter_name = f"tag_path_{index}"
        conditions.append(
            f"""
            EXISTS (
                SELECT 1
                FROM proc.case_document_tag_memberships tag_filter_{index}
                WHERE tag_filter_{index}.case_document_id = cd.case_document_id
                  AND tag_filter_{index}.tag_path = %({parameter_name})s
            )
            """
        )
        parameters[parameter_name] = tag_path

    normalized_status = (execution_status or "all").strip().lower()
    if normalized_status not in VALID_CASE_DOC_EXECUTION_STATUSES:
        raise ValueError("execution_status is invalid.")
    if normalized_status == "active":
        conditions.append("cd.status = 'active'")
    elif normalized_status == "not_started":
        conditions.extend(
            [
                "cd.status = 'active'",
                """
                NOT EXISTS (
                    SELECT 1
                    FROM proc.case_document_execution_items started_item
                    WHERE started_item.case_document_id = cd.case_document_id
                      AND started_item.status IN ('checked', 'skipped')
                )
                """,
            ]
        )
    elif normalized_status == "in_progress":
        conditions.extend(
            [
                "cd.status = 'active'",
                """
                EXISTS (
                    SELECT 1
                    FROM proc.case_document_execution_items started_item
                    WHERE started_item.case_document_id = cd.case_document_id
                      AND started_item.status IN ('checked', 'skipped')
                )
                """,
            ]
        )
    elif normalized_status == "completed":
        conditions.append("cd.status = 'completed'")

    return ("WHERE " + " AND ".join(conditions) if conditions else "", parameters)


def create_case_doc_instance(
    settings: AppSettings,
    source_doc: SourceDocDetailData,
    context: CaseDocResolveContextData,
    workbook_bytes: bytes,
    execution_item_snapshots: Sequence[dict[str, Any]],
    created_by: str | None,
    case_name: str | None = None,
) -> CaseDocInstanceDetailData:
    """Persist a generated workbook and its executable time cells."""

    case_document_key = f"CASE-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6].upper()}"
    workbook_path: Path | None = None

    try:
        import psycopg
        from psycopg.rows import dict_row

        workbook_path = _write_original_workbook(settings, case_document_key, workbook_bytes)
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    """
                    INSERT INTO proc.case_documents (
                        case_document_key,
                        case_name,
                        source_doc_id,
                        source_doc_version_id,
                        source_doc_key,
                        source_doc_name,
                        unit_config_id,
                        prefecture,
                        building,
                        context_json,
                        preparation_json,
                        workbook_path,
                        created_by
                    ) VALUES (
                        %(case_document_key)s,
                        %(case_name)s,
                        %(source_doc_id)s,
                        %(source_doc_version_id)s,
                        %(source_doc_key)s,
                        %(source_doc_name)s,
                        %(unit_config_id)s,
                        %(prefecture)s,
                        %(building)s,
                        %(context_json)s::jsonb,
                        %(preparation_json)s::jsonb,
                        %(workbook_path)s,
                        %(created_by)s
                    )
                    RETURNING case_document_id;
                    """,
                    {
                        "case_document_key": case_document_key,
                        "case_name": (case_name or "").strip() or source_doc.source_doc_name,
                        "source_doc_id": source_doc.source_doc_id,
                        "source_doc_version_id": source_doc.source_doc_version_id,
                        "source_doc_key": source_doc.source_doc_key,
                        "source_doc_name": source_doc.source_doc_name,
                        "unit_config_id": context.unit_config.unit_config_id,
                        "prefecture": context.unit_config.prefecture,
                        "building": context.unit_config.building,
                        "context_json": json.dumps(context.model_dump(mode="json"), ensure_ascii=False),
                        "preparation_json": json.dumps(
                            {
                                "construction_name": "",
                                "construction_date": None,
                                "construction_executor": "",
                                "block": context.unit_config.block,
                                "target_fs": context.unit_config.fs_cluster_name,
                                "updated_by": None,
                                "updated_at": None,
                            },
                            ensure_ascii=False,
                        ),
                        "workbook_path": str(workbook_path),
                        "created_by": created_by,
                    },
                )
                inserted = cursor.fetchone()
                if inserted is None:
                    raise RuntimeError("case document insert returned no identifier")
                case_document_id = int(inserted["case_document_id"])

                for tag_path in _normalize_case_doc_tag_paths(source_doc.tag_paths):
                    cursor.execute(
                        """
                        INSERT INTO proc.case_document_tag_memberships (case_document_id, tag_path)
                        VALUES (%(case_document_id)s, %(tag_path)s)
                        ON CONFLICT (case_document_id, tag_path) DO NOTHING;
                        """,
                        {"case_document_id": case_document_id, "tag_path": tag_path},
                    )
                cursor.execute(
                    """
                    UPDATE proc.case_documents
                    SET tags_initialized = true
                    WHERE case_document_id = %(case_document_id)s;
                    """,
                    {"case_document_id": case_document_id},
                )

                for target in context.target_device_slots:
                    cursor.execute(
                        """
                        INSERT INTO proc.case_document_targets (
                            case_document_id, target_no, slot_key, device_type, system, host_name
                        ) VALUES (
                            %(case_document_id)s, %(target_no)s, %(slot_key)s,
                            %(device_type)s, %(system)s, %(host_name)s
                        );
                        """,
                        {
                            "case_document_id": case_document_id,
                            "target_no": target.excel_no,
                            "slot_key": target.slot_key,
                            "device_type": target.device_type,
                            "system": target.system,
                            "host_name": target.host_name,
                        },
                    )

                for item in execution_item_snapshots:
                    cursor.execute(
                        """
                        INSERT INTO proc.case_document_execution_items (
                            case_document_id,
                            module_row_id,
                            row_order,
                            target_no,
                            excel_cell,
                            major_no,
                            middle_no,
                            minor_no,
                            tech_doc_text,
                            work_text,
                            check_text,
                            window_text,
                            p_text,
                            command_text
                        ) VALUES (
                            %(case_document_id)s,
                            %(module_row_id)s,
                            %(row_order)s,
                            %(target_no)s,
                            %(excel_cell)s,
                            %(major_no)s,
                            %(middle_no)s,
                            %(minor_no)s,
                            %(tech_doc_text)s,
                            %(work_text)s,
                            %(check_text)s,
                            %(window_text)s,
                            %(p_text)s,
                            %(command_text)s
                        );
                        """,
                        {"case_document_id": case_document_id, **item},
                    )
    except Exception as exception:
        if workbook_path is not None:
            workbook_path.unlink(missing_ok=True)
        if isinstance(exception, (ValueError, DatabaseConnectionError)):
            raise
        raise DatabaseConnectionError("案件CS実行データの保存に失敗しました。") from exception

    detail = get_case_doc_instance_detail(settings, case_document_id)
    if detail is None:
        raise DatabaseConnectionError("保存した案件CS実行データを取得できませんでした。")
    return detail


def list_case_doc_instances(
    settings: AppSettings,
    keyword: str | None = None,
    tag_paths: Sequence[str] | None = None,
    execution_status: str | None = None,
) -> CaseDocInstanceListData:
    """Return persistent case document instances ordered by newest first."""

    where_clause, parameters = _build_case_doc_list_filter(keyword, tag_paths, execution_status)

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    f"{CASE_DOC_SUMMARY_SELECT} {where_clause} {CASE_DOC_SUMMARY_GROUP} ORDER BY cd.created_at DESC",
                    parameters,
                )
                rows = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT DISTINCT membership.tag_path
                    FROM proc.case_document_tag_memberships membership
                    JOIN proc.case_documents cd
                      ON cd.case_document_id = membership.case_document_id
                    ORDER BY membership.tag_path;
                    """
                )
                tags = [str(row["tag_path"]) for row in cursor.fetchall()]
    except Exception as exception:
        raise DatabaseConnectionError("案件CS実行一覧の取得に失敗しました。") from exception

    return CaseDocInstanceListData(items=[_summary_from_row(row) for row in rows], tags=tags)


def get_case_doc_instance_detail(
    settings: AppSettings,
    case_document_id: int,
) -> CaseDocInstanceDetailData | None:
    """Return one persistent case document instance with execution history."""

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    f"{CASE_DOC_SUMMARY_SELECT} WHERE cd.case_document_id = %(case_document_id)s "
                    f"{CASE_DOC_SUMMARY_GROUP}",
                    {"case_document_id": case_document_id},
                )
                summary_row = cursor.fetchone()
                if summary_row is None:
                    return None

                cursor.execute(
                    """
                    SELECT target_no, slot_key, device_type, system, host_name
                    FROM proc.case_document_targets
                    WHERE case_document_id = %(case_document_id)s
                    ORDER BY target_no;
                    """,
                    {"case_document_id": case_document_id},
                )
                target_rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT
                        cei.execution_item_id,
                        cei.row_order,
                        cei.module_row_id,
                        cei.target_no,
                        cdt.host_name,
                        cei.excel_cell,
                        cei.major_no,
                        cei.middle_no,
                        cei.minor_no,
                        cei.tech_doc_text,
                        cei.work_text,
                        cei.check_text,
                        cei.window_text,
                        cei.p_text,
                        cei.command_text,
                        cei.status,
                        cei.performed_at,
                        cei.performed_by,
                        cei.skip_reason,
                        cei.lock_version
                    FROM proc.case_document_execution_items cei
                    JOIN proc.case_document_targets cdt
                      ON cdt.case_document_id = cei.case_document_id
                     AND cdt.target_no = cei.target_no
                    WHERE cei.case_document_id = %(case_document_id)s
                    ORDER BY cei.row_order, cei.target_no;
                    """,
                    {"case_document_id": case_document_id},
                )
                item_rows = cursor.fetchall()

                module_row_ids = sorted(
                    {
                        int(row["module_row_id"])
                        for row in item_rows
                        if row["module_row_id"] is not None
                    }
                )
                images_by_module_row_id: dict[int, list[ModuleRowImageData]] = {
                    module_row_id: [] for module_row_id in module_row_ids
                }
                if module_row_ids:
                    cursor.execute(
                        """
                        SELECT
                            module_row_id,
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
                        WHERE module_row_id = ANY(%(module_row_ids)s)
                        ORDER BY module_row_id, image_order, module_row_image_id;
                        """,
                        {"module_row_ids": module_row_ids},
                    )
                    for image_row in cursor.fetchall():
                        images_by_module_row_id[int(image_row["module_row_id"])].append(
                            ModuleRowImageData(
                                module_row_image_id=int(image_row["module_row_image_id"]),
                                image_key=str(image_row["image_key"]),
                                image_path=str(image_row["image_path"]),
                                anchor_cell=str(image_row["anchor_cell"]),
                                offset_x_px=int(image_row["offset_x_px"] or 0),
                                offset_y_px=int(image_row["offset_y_px"] or 0),
                                width_px=(
                                    int(image_row["width_px"])
                                    if image_row["width_px"] is not None
                                    else None
                                ),
                                height_px=(
                                    int(image_row["height_px"])
                                    if image_row["height_px"] is not None
                                    else None
                                ),
                                image_order=int(image_row["image_order"] or 1),
                            )
                        )

                item_ids = [row["execution_item_id"] for row in item_rows]
                history_by_item: dict[int, list[CaseDocExecutionHistoryData]] = {item_id: [] for item_id in item_ids}
                if item_ids:
                    cursor.execute(
                        """
                        SELECT history_id, execution_item_id, from_status, to_status,
                               changed_at, changed_by, note
                        FROM proc.case_document_execution_histories
                        WHERE execution_item_id = ANY(%(item_ids)s)
                        ORDER BY changed_at, history_id;
                        """,
                        {"item_ids": item_ids},
                    )
                    for history_row in cursor.fetchall():
                        history_by_item[history_row["execution_item_id"]].append(
                            CaseDocExecutionHistoryData(
                                history_id=history_row["history_id"],
                                from_status=history_row["from_status"],
                                to_status=history_row["to_status"],
                                changed_at=_isoformat(history_row["changed_at"]) or "",
                                changed_by=history_row["changed_by"],
                                note=history_row["note"],
                            )
                        )

                cursor.execute(
                    """
                    SELECT
                        group_start_row_order,
                        item_label,
                        comment_text,
                        updated_by,
                        updated_at,
                        lock_version
                    FROM proc.case_document_execution_comments
                    WHERE case_document_id = %(case_document_id)s
                    ORDER BY group_start_row_order;
                    """,
                    {"case_document_id": case_document_id},
                )
                comment_rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("案件CS実行詳細の取得に失敗しました。") from exception

    summary = _summary_from_row(summary_row)
    targets = [
        CaseDocTargetDeviceSlotData(
            excel_no=row["target_no"],
            slot_key=row["slot_key"],
            device_type=row["device_type"],
            system=row["system"],
            host_name=row["host_name"],
        )
        for row in target_rows
    ]
    execution_items = [
        CaseDocExecutionItemData(
            execution_item_id=row["execution_item_id"],
            row_order=row["row_order"],
            module_row_id=row["module_row_id"],
            target_no=row["target_no"],
            host_name=row["host_name"],
            excel_cell=row["excel_cell"],
            major_no=row["major_no"],
            middle_no=row["middle_no"],
            minor_no=row["minor_no"],
            tech_doc_text=row["tech_doc_text"],
            work_text=row["work_text"],
            check_text=row["check_text"],
            window_text=row["window_text"],
            p_text=row["p_text"],
            command_text=row["command_text"],
            status=row["status"],
            performed_at=_isoformat(row["performed_at"]),
            performed_by=row["performed_by"],
            skip_reason=row["skip_reason"],
            lock_version=row["lock_version"],
            images=(
                images_by_module_row_id.get(int(row["module_row_id"]), [])
                if row["module_row_id"] is not None
                else []
            ),
            histories=history_by_item[row["execution_item_id"]],
        )
        for row in item_rows
    ]
    execution_comments = [
        CaseDocExecutionCommentData(
            group_start_row_order=row["group_start_row_order"],
            item_label=row["item_label"],
            comment_text=row["comment_text"],
            updated_by=row["updated_by"],
            updated_at=_isoformat(row["updated_at"]) or "",
            lock_version=row["lock_version"],
        )
        for row in comment_rows
    ]
    return CaseDocInstanceDetailData(
        **summary.model_dump(),
        prefecture=summary_row["prefecture"],
        building=summary_row["building"],
        preparation=_preparation_from_row(summary_row),
        targets=targets,
        execution_items=execution_items,
        execution_comments=execution_comments,
    )


def update_case_doc_preparation(
    settings: AppSettings,
    case_document_id: int,
    payload: CaseDocPreparationUpdateRequest,
) -> CaseDocInstanceDetailData:
    """Save preparation values before case document execution."""

    preparation = payload.model_dump(mode="json")
    preparation["updated_at"] = datetime.now().astimezone().isoformat()

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    """
                    UPDATE proc.case_documents
                    SET preparation_json = %(preparation_json)s::jsonb,
                        updated_at = now()
                    WHERE case_document_id = %(case_document_id)s
                      AND status = 'active'
                    RETURNING case_document_id;
                    """,
                    {
                        "case_document_id": case_document_id,
                        "preparation_json": json.dumps(preparation, ensure_ascii=False),
                    },
                )
                if cursor.fetchone() is None:
                    raise ValueError("案件CSが見つからないか、すでに完了しています。")
    except ValueError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("案件CSの工事情報保存に失敗しました。") from exception

    detail = get_case_doc_instance_detail(settings, case_document_id)
    if detail is None:
        raise DatabaseConnectionError("保存した案件CSの工事情報を取得できませんでした。")
    return detail


def update_case_doc_execution_item(
    settings: AppSettings,
    case_document_id: int,
    execution_item_id: int,
    payload: CaseDocExecutionUpdateRequest,
) -> CaseDocInstanceDetailData:
    """Update one time-cell state using optimistic locking."""

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    """
                    SELECT
                        cei.status,
                        cd.status AS case_document_status,
                        cd.preparation_json
                    FROM proc.case_document_execution_items cei
                    JOIN proc.case_documents cd ON cd.case_document_id = cei.case_document_id
                    WHERE cei.execution_item_id = %(execution_item_id)s
                      AND cei.case_document_id = %(case_document_id)s;
                    """,
                    {
                        "execution_item_id": execution_item_id,
                        "case_document_id": case_document_id,
                    },
                )
                current = cursor.fetchone()
                if current is None:
                    raise ValueError("案件CSの実施項目が見つかりませんでした。")
                if current["case_document_status"] != "active":
                    raise ValueError("完了済みの案件CSは変更できません。")
                if not _is_preparation_complete(current["preparation_json"]):
                    raise ValueError("工事情報を入力して保存してから案件CSを実行してください。")

                cursor.execute(
                    """
                    UPDATE proc.case_document_execution_items
                    SET
                        status = %(status)s,
                        performed_at = CASE WHEN %(status)s = 'pending' THEN NULL ELSE now() END,
                        performed_by = CASE WHEN %(status)s = 'pending' THEN NULL ELSE %(performed_by)s END,
                        skip_reason = CASE WHEN %(status)s = 'skipped' THEN %(skip_reason)s ELSE NULL END,
                        lock_version = lock_version + 1,
                        updated_at = now()
                    WHERE execution_item_id = %(execution_item_id)s
                      AND case_document_id = %(case_document_id)s
                      AND lock_version = %(expected_lock_version)s
                    RETURNING execution_item_id;
                    """,
                    {
                        "status": payload.status,
                        "performed_by": payload.performed_by,
                        "skip_reason": payload.skip_reason,
                        "execution_item_id": execution_item_id,
                        "case_document_id": case_document_id,
                        "expected_lock_version": payload.expected_lock_version,
                    },
                )
                if cursor.fetchone() is None:
                    raise ValueError("ほかの操作で更新されています。画面を再読み込みしてください。")

                cursor.execute(
                    """
                    INSERT INTO proc.case_document_execution_histories (
                        execution_item_id, from_status, to_status, changed_by, note
                    ) VALUES (
                        %(execution_item_id)s, %(from_status)s, %(to_status)s,
                        %(changed_by)s, %(note)s
                    );
                    """,
                    {
                        "execution_item_id": execution_item_id,
                        "from_status": current["status"],
                        "to_status": payload.status,
                        "changed_by": payload.performed_by,
                        "note": payload.skip_reason,
                    },
                )
                cursor.execute(
                    """
                    UPDATE proc.case_documents
                    SET updated_at = now()
                    WHERE case_document_id = %(case_document_id)s;
                    """,
                    {"case_document_id": case_document_id},
                )
    except ValueError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("案件CSの実施状態更新に失敗しました。") from exception

    detail = get_case_doc_instance_detail(settings, case_document_id)
    if detail is None:
        raise DatabaseConnectionError("更新した案件CS実行データを取得できませんでした。")
    return detail


def update_case_doc_execution_items(
    settings: AppSettings,
    case_document_id: int,
    payload: CaseDocExecutionBulkUpdateRequest,
    performed_by: str,
) -> CaseDocInstanceDetailData:
    """Atomically update only pending cells, preserving every prior result."""

    item_versions = {item.execution_item_id: item.expected_lock_version for item in payload.items}
    if len(item_versions) != len(payload.items):
        raise ValueError("同じ実施項目が複数選択されています。")
    item_ids = sorted(item_versions)

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    """
                    SELECT execution_item_id, status, lock_version
                    FROM proc.case_document_execution_items
                    WHERE case_document_id = %(case_document_id)s
                      AND execution_item_id = ANY(%(item_ids)s)
                    ORDER BY execution_item_id
                    FOR UPDATE;
                    """,
                    {"case_document_id": case_document_id, "item_ids": item_ids},
                )
                selected = cursor.fetchall()
                if len(selected) != len(item_ids):
                    raise ValueError("対象の実施項目が見つかりません。画面を再読み込みしてください。")
                if any(row["status"] != "pending" for row in selected):
                    raise ValueError("実施済みの項目は一括更新できません。画面を再読み込みしてください。")
                if any(row["lock_version"] != item_versions[row["execution_item_id"]] for row in selected):
                    raise ValueError("ほかの操作で更新されています。画面を再読み込みしてください。")

                cursor.execute(
                    """
                    SELECT status, preparation_json
                    FROM proc.case_documents
                    WHERE case_document_id = %(case_document_id)s
                    FOR UPDATE;
                    """,
                    {"case_document_id": case_document_id},
                )
                case_document = cursor.fetchone()
                if case_document is None or case_document["status"] != "active":
                    raise ValueError("案件CSが見つからないか、すでに完了しています。")
                if not _is_preparation_complete(case_document["preparation_json"]):
                    raise ValueError("工事情報を入力して保存してから案件CSを実行してください。")

                cursor.execute(
                    """
                    UPDATE proc.case_document_execution_items
                    SET status = %(status)s,
                        performed_at = now(),
                        performed_by = %(performed_by)s,
                        skip_reason = %(skip_reason)s,
                        lock_version = lock_version + 1,
                        updated_at = now()
                    WHERE case_document_id = %(case_document_id)s
                      AND execution_item_id = ANY(%(item_ids)s)
                      AND status = 'pending'
                    RETURNING execution_item_id;
                    """,
                    {
                        "status": payload.status,
                        "performed_by": performed_by,
                        "skip_reason": payload.skip_reason if payload.status == "skipped" else None,
                        "case_document_id": case_document_id,
                        "item_ids": item_ids,
                    },
                )
                if len(cursor.fetchall()) != len(item_ids):
                    raise ValueError("ほかの操作で更新されています。画面を再読み込みしてください。")

                cursor.execute(
                    """
                    INSERT INTO proc.case_document_execution_histories (
                        execution_item_id, from_status, to_status, changed_by, note
                    )
                    SELECT execution_item_id, 'pending', %(status)s, %(performed_by)s, %(note)s
                    FROM proc.case_document_execution_items
                    WHERE case_document_id = %(case_document_id)s
                      AND execution_item_id = ANY(%(item_ids)s);
                    """,
                    {
                        "status": payload.status,
                        "performed_by": performed_by,
                        "note": payload.skip_reason if payload.status == "skipped" else None,
                        "case_document_id": case_document_id,
                        "item_ids": item_ids,
                    },
                )
                cursor.execute(
                    """
                    UPDATE proc.case_documents
                    SET updated_at = now()
                    WHERE case_document_id = %(case_document_id)s;
                    """,
                    {"case_document_id": case_document_id},
                )
    except ValueError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("案件CSの一括更新に失敗しました。") from exception

    detail = get_case_doc_instance_detail(settings, case_document_id)
    if detail is None:
        raise DatabaseConnectionError("更新した案件CS実行データを取得できませんでした。")
    return detail


def update_case_doc_execution_comment(
    settings: AppSettings,
    case_document_id: int,
    group_start_row_order: int,
    payload: CaseDocExecutionCommentUpdateRequest,
    updated_by: str,
) -> CaseDocInstanceDetailData:
    """Save one optional comment against a minor-number execution group."""

    comment_text = payload.comment_text.strip()
    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    """
                    SELECT status, preparation_json
                    FROM proc.case_documents
                    WHERE case_document_id = %(case_document_id)s
                    FOR UPDATE;
                    """,
                    {"case_document_id": case_document_id},
                )
                case_document = cursor.fetchone()
                if case_document is None or case_document["status"] != "active":
                    raise ValueError("案件CSが見つからないか、すでに完了しています。")
                if not _is_preparation_complete(case_document["preparation_json"]):
                    raise ValueError("工事情報を入力して保存してからコメントを登録してください。")

                cursor.execute(
                    """
                    SELECT
                        major_no,
                        middle_no,
                        minor_no,
                        (
                            SELECT MIN(first_item.row_order)
                            FROM proc.case_document_execution_items first_item
                            WHERE first_item.case_document_id = %(case_document_id)s
                        ) AS first_row_order
                    FROM proc.case_document_execution_items
                    WHERE case_document_id = %(case_document_id)s
                      AND row_order = %(group_start_row_order)s
                    ORDER BY target_no
                    LIMIT 1;
                    """,
                    {
                        "case_document_id": case_document_id,
                        "group_start_row_order": group_start_row_order,
                    },
                )
                group_row = cursor.fetchone()
                if group_row is None:
                    raise ValueError("指定された小項番が見つかりません。")
                if not str(group_row["minor_no"] or "").strip() and group_start_row_order != group_row["first_row_order"]:
                    raise ValueError("コメントは小項番の先頭行に登録してください。")

                number_parts = [
                    str(group_row[key] or "").strip()
                    for key in ("major_no", "middle_no", "minor_no")
                ]
                item_label = ".".join(part for part in number_parts if part) or "番号なし"

                cursor.execute(
                    """
                    SELECT lock_version
                    FROM proc.case_document_execution_comments
                    WHERE case_document_id = %(case_document_id)s
                      AND group_start_row_order = %(group_start_row_order)s
                    FOR UPDATE;
                    """,
                    {
                        "case_document_id": case_document_id,
                        "group_start_row_order": group_start_row_order,
                    },
                )
                existing_comment = cursor.fetchone()
                current_lock_version = int(existing_comment["lock_version"]) if existing_comment else 0
                if current_lock_version != payload.expected_lock_version:
                    raise ValueError("ほかの操作でコメントが更新されています。画面を再読み込みしてください。")

                parameters = {
                    "case_document_id": case_document_id,
                    "group_start_row_order": group_start_row_order,
                    "item_label": item_label,
                    "comment_text": comment_text,
                    "updated_by": updated_by,
                    "expected_lock_version": payload.expected_lock_version,
                }
                if existing_comment is None:
                    cursor.execute(
                        """
                        INSERT INTO proc.case_document_execution_comments (
                            case_document_id,
                            group_start_row_order,
                            item_label,
                            comment_text,
                            updated_by,
                            lock_version
                        ) VALUES (
                            %(case_document_id)s,
                            %(group_start_row_order)s,
                            %(item_label)s,
                            %(comment_text)s,
                            %(updated_by)s,
                            1
                        );
                        """,
                        parameters,
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE proc.case_document_execution_comments
                        SET item_label = %(item_label)s,
                            comment_text = %(comment_text)s,
                            updated_by = %(updated_by)s,
                            updated_at = now(),
                            lock_version = lock_version + 1
                        WHERE case_document_id = %(case_document_id)s
                          AND group_start_row_order = %(group_start_row_order)s
                          AND lock_version = %(expected_lock_version)s
                        RETURNING execution_comment_id;
                        """,
                        parameters,
                    )
                    if cursor.fetchone() is None:
                        raise ValueError("ほかの操作でコメントが更新されています。画面を再読み込みしてください。")

                cursor.execute(
                    """
                    UPDATE proc.case_documents
                    SET updated_at = now()
                    WHERE case_document_id = %(case_document_id)s;
                    """,
                    {"case_document_id": case_document_id},
                )
    except ValueError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("案件CSのコメント保存に失敗しました。") from exception

    detail = get_case_doc_instance_detail(settings, case_document_id)
    if detail is None:
        raise DatabaseConnectionError("コメントを保存した案件CS実行データを取得できませんでした。")
    return detail


def complete_case_doc_instance(settings: AppSettings, case_document_id: int) -> CaseDocInstanceDetailData:
    """Complete an instance after every execution item has a result."""

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    """
                    SELECT status, preparation_json
                    FROM proc.case_documents
                    WHERE case_document_id = %(case_document_id)s;
                    """,
                    {"case_document_id": case_document_id},
                )
                case_document = cursor.fetchone()
                if case_document is None:
                    raise ValueError("案件CSが見つかりませんでした。")
                if case_document["status"] != "active":
                    raise ValueError("案件CSが見つからないか、すでに完了しています。")
                if not _is_preparation_complete(case_document["preparation_json"]):
                    raise ValueError("工事情報を入力して保存してから案件CSを実行してください。")

                cursor.execute(
                    """
                    SELECT COUNT(*)::integer AS pending_count
                    FROM proc.case_document_execution_items
                    WHERE case_document_id = %(case_document_id)s
                      AND status = 'pending';
                    """,
                    {"case_document_id": case_document_id},
                )
                pending = cursor.fetchone()
                if pending is None:
                    raise ValueError("案件CSが見つかりませんでした。")
                if pending["pending_count"] > 0:
                    raise ValueError("未実施の項目があるため完了できません。")
                cursor.execute(
                    """
                    UPDATE proc.case_documents
                    SET status = 'completed', completed_at = now(), updated_at = now()
                    WHERE case_document_id = %(case_document_id)s
                      AND status = 'active'
                    RETURNING case_document_id;
                    """,
                    {"case_document_id": case_document_id},
                )
                if cursor.fetchone() is None:
                    raise ValueError("案件CSが見つからないか、すでに完了しています。")
    except ValueError:
        raise
    except Exception as exception:
        raise DatabaseConnectionError("案件CSの完了処理に失敗しました。") from exception

    detail = get_case_doc_instance_detail(settings, case_document_id)
    if detail is None:
        raise DatabaseConnectionError("完了した案件CS実行データを取得できませんでした。")
    return detail


def read_case_doc_original_workbook(settings: AppSettings, case_document_id: int) -> bytes:
    """Read the immutable original workbook stored for one instance."""

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(
                    """
                    SELECT workbook_path
                    FROM proc.case_documents
                    WHERE case_document_id = %(case_document_id)s;
                    """,
                    {"case_document_id": case_document_id},
                )
                row = cursor.fetchone()
    except Exception as exception:
        raise DatabaseConnectionError("案件CSファイル情報の取得に失敗しました。") from exception

    if row is None:
        raise ValueError("案件CSが見つかりませんでした。")
    workbook_path = Path(row["workbook_path"])
    if not workbook_path.is_file():
        raise ValueError("案件CSの元Excelが見つかりませんでした。")
    return workbook_path.read_bytes()
