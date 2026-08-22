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
    CaseDocExecutionHistoryData,
    CaseDocExecutionItemData,
    CaseDocExecutionUpdateRequest,
    CaseDocInstanceDetailData,
    CaseDocInstanceListData,
    CaseDocInstanceListItemData,
    CaseDocResolveContextData,
    CaseDocTargetDeviceSlotData,
    SourceDocDetailData,
)


CASE_DOC_INSTANCE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS proc.case_documents (
    case_document_id bigserial PRIMARY KEY,
    case_document_key text NOT NULL UNIQUE,
    source_doc_id bigint NOT NULL,
    source_doc_version_id bigint NOT NULL,
    source_doc_key text NOT NULL,
    source_doc_name text NOT NULL,
    unit_config_id text NOT NULL,
    prefecture text NOT NULL,
    building text NOT NULL,
    context_json jsonb NOT NULL,
    workbook_path text NOT NULL,
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
    created_by text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

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


def _ensure_schema(cursor: Any) -> None:
    cursor.execute(CASE_DOC_INSTANCE_SCHEMA_SQL)


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
        source_doc_id=row["source_doc_id"],
        source_doc_key=row["source_doc_key"],
        source_doc_name=row["source_doc_name"],
        unit_config_id=row["unit_config_id"],
        status=row["status"],
        total_count=row["total_count"],
        checked_count=row["checked_count"],
        skipped_count=row["skipped_count"],
        pending_count=row["pending_count"],
        created_by=row["created_by"],
        created_at=_isoformat(row["created_at"]) or "",
        updated_at=_isoformat(row["updated_at"]) or "",
    )


CASE_DOC_SUMMARY_SELECT = """
SELECT
    cd.case_document_id,
    cd.case_document_key,
    cd.source_doc_id,
    cd.source_doc_key,
    cd.source_doc_name,
    cd.unit_config_id,
    cd.status,
    COUNT(cei.execution_item_id)::integer AS total_count,
    COUNT(*) FILTER (WHERE cei.status = 'checked')::integer AS checked_count,
    COUNT(*) FILTER (WHERE cei.status = 'skipped')::integer AS skipped_count,
    COUNT(*) FILTER (WHERE cei.status = 'pending')::integer AS pending_count,
    cd.created_by,
    cd.created_at,
    cd.updated_at,
    cd.prefecture,
    cd.building,
    cd.workbook_path
FROM proc.case_documents cd
LEFT JOIN proc.case_document_execution_items cei
    ON cei.case_document_id = cd.case_document_id
"""


CASE_DOC_SUMMARY_GROUP = """
GROUP BY
    cd.case_document_id,
    cd.case_document_key,
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
    cd.workbook_path
"""


def create_case_doc_instance(
    settings: AppSettings,
    source_doc: SourceDocDetailData,
    context: CaseDocResolveContextData,
    workbook_bytes: bytes,
    execution_item_snapshots: Sequence[dict[str, Any]],
    created_by: str | None,
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
                        source_doc_id,
                        source_doc_version_id,
                        source_doc_key,
                        source_doc_name,
                        unit_config_id,
                        prefecture,
                        building,
                        context_json,
                        workbook_path,
                        created_by
                    ) VALUES (
                        %(case_document_key)s,
                        %(source_doc_id)s,
                        %(source_doc_version_id)s,
                        %(source_doc_key)s,
                        %(source_doc_name)s,
                        %(unit_config_id)s,
                        %(prefecture)s,
                        %(building)s,
                        %(context_json)s::jsonb,
                        %(workbook_path)s,
                        %(created_by)s
                    )
                    RETURNING case_document_id;
                    """,
                    {
                        "case_document_key": case_document_key,
                        "source_doc_id": source_doc.source_doc_id,
                        "source_doc_version_id": source_doc.source_doc_version_id,
                        "source_doc_key": source_doc.source_doc_key,
                        "source_doc_name": source_doc.source_doc_name,
                        "unit_config_id": context.unit_config.unit_config_id,
                        "prefecture": context.unit_config.prefecture,
                        "building": context.unit_config.building,
                        "context_json": json.dumps(context.model_dump(mode="json"), ensure_ascii=False),
                        "workbook_path": str(workbook_path),
                        "created_by": created_by,
                    },
                )
                inserted = cursor.fetchone()
                if inserted is None:
                    raise RuntimeError("case document insert returned no identifier")
                case_document_id = int(inserted["case_document_id"])

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


def list_case_doc_instances(settings: AppSettings) -> CaseDocInstanceListData:
    """Return persistent case document instances ordered by newest first."""

    try:
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                _ensure_schema(cursor)
                cursor.execute(f"{CASE_DOC_SUMMARY_SELECT} {CASE_DOC_SUMMARY_GROUP} ORDER BY cd.created_at DESC")
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("案件CS実行一覧の取得に失敗しました。") from exception

    return CaseDocInstanceListData(items=[_summary_from_row(row) for row in rows])


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
            histories=history_by_item[row["execution_item_id"]],
        )
        for row in item_rows
    ]
    return CaseDocInstanceDetailData(
        **summary.model_dump(),
        prefecture=summary_row["prefecture"],
        building=summary_row["building"],
        targets=targets,
        execution_items=execution_items,
    )


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
                    SELECT cei.status, cd.status AS case_document_status
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
