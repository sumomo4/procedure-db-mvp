"""Database access helpers for approval status resources."""

from datetime import date, datetime
from typing import Any

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApprovalStatusHistoryItemData,
    ApprovalStatusDetailData,
    ApprovalStatusListData,
    ApprovalStatusListItemData,
    ApprovalTransitionData,
)
from app.db.source_docs import SOURCE_DOC_STATUS_LABELS


APPROVAL_TARGET_TYPE = "source-doc"
APPROVAL_NEXT_ACTIONS = {
    "draft": "承認または差戻し",
    "published": "保管する",
    "archived": "確認のみ",
}
APPROVAL_ALLOWED_TRANSITIONS = {
    "draft": [("published", "承認する"), ("draft", "差戻す")],
    "published": [("archived", "保管する")],
    "archived": [],
}


def _format_updated_at(value: Any) -> str:
    """Format DB timestamp/date values for API responses."""

    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _format_changed_at(value: Any) -> str:
    """Format DB timestamp values for approval history responses."""

    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _ensure_history_table(cursor: Any) -> None:
    """Create the approval history table when existing DB volumes predate it."""

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS proc.approval_status_histories (
            approval_status_history_id bigserial PRIMARY KEY,
            target_type text NOT NULL CHECK (target_type IN ('source-doc')),
            target_id bigint NOT NULL,
            target_version_id bigint NOT NULL REFERENCES proc.blueprint_versions (blueprint_version_id) ON DELETE CASCADE,
            from_status text CHECK (from_status IN ('draft', 'published', 'archived')),
            to_status text NOT NULL CHECK (to_status IN ('draft', 'published', 'archived')),
            action_label text NOT NULL,
            changed_by text,
            changed_at timestamptz NOT NULL DEFAULT now(),
            note text
        );
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_approval_status_histories_target
            ON proc.approval_status_histories (target_type, target_id, changed_at DESC);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_approval_status_histories_version
            ON proc.approval_status_histories (target_version_id);
        """
    )


def _build_history_items(rows: list[Any]) -> list[ApprovalStatusHistoryItemData]:
    """Build approval history response items."""

    return [
        ApprovalStatusHistoryItemData(
            history_id=row[0],
            from_status=row[1],
            from_status_label=SOURCE_DOC_STATUS_LABELS.get(row[1], row[1]) if row[1] is not None else None,
            to_status=row[2],
            to_status_label=SOURCE_DOC_STATUS_LABELS.get(row[2], row[2]),
            action_label=row[3],
            changed_by=row[4],
            changed_at=_format_changed_at(row[5]),
            note=row[6],
        )
        for row in rows
    ]


def _build_transition_data(status_value: str) -> list[ApprovalTransitionData]:
    """Build allowed transitions for a status value."""

    return [
        ApprovalTransitionData(
            to_status=to_status,
            to_status_label=SOURCE_DOC_STATUS_LABELS.get(to_status, to_status),
            action_label=action_label,
        )
        for to_status, action_label in APPROVAL_ALLOWED_TRANSITIONS.get(status_value, [])
    ]


def list_statuses(settings: AppSettings) -> ApprovalStatusListData:
    """Read approval targets from PostgreSQL."""

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    query = """
        WITH latest_versions AS (
            SELECT DISTINCT ON (bv.blueprint_id)
                bv.blueprint_version_id,
                bv.blueprint_id,
                bv.version_no,
                bv.status,
                bv.change_note,
                bv.created_by,
                bv.updated_at
            FROM proc.blueprint_versions bv
            ORDER BY bv.blueprint_id, bv.version_no DESC
        )
        SELECT
            b.blueprint_id,
            b.blueprint_key,
            b.name AS target_name,
            lv.version_no,
            lv.status,
            COUNT(bi.blueprint_item_id)::int AS module_count,
            COUNT(*) FILTER (WHERE COALESCE(bi.enabled, false))::int AS enabled_module_count,
            lv.created_by,
            lv.updated_at
        FROM proc.blueprints b
        JOIN latest_versions lv
            ON lv.blueprint_id = b.blueprint_id
        LEFT JOIN proc.blueprint_items bi
            ON bi.blueprint_version_id = lv.blueprint_version_id
        GROUP BY
            b.blueprint_id,
            b.blueprint_key,
            b.name,
            lv.version_no,
            lv.status,
            lv.created_by,
            lv.updated_at
        ORDER BY b.blueprint_key;
    """

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, {})
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Approval status list query failed.") from exception

    items = [
        ApprovalStatusListItemData(
            target_id=row[0],
            target_key=row[1],
            target_name=row[2],
            target_type=APPROVAL_TARGET_TYPE,
            version_no=row[3],
            status=row[4],
            status_label=SOURCE_DOC_STATUS_LABELS.get(row[4], row[4]),
            next_action=APPROVAL_NEXT_ACTIONS.get(row[4], "確認のみ"),
            module_count=row[5],
            enabled_module_count=row[6],
            created_by=row[7],
            updated_at=_format_updated_at(row[8]),
        )
        for row in rows
    ]

    return ApprovalStatusListData(items=items)


def get_status_detail(settings: AppSettings, target_id: int) -> ApprovalStatusDetailData | None:
    """Read one approval target detail from PostgreSQL."""

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
                bv.updated_at
            FROM proc.blueprint_versions bv
            WHERE bv.blueprint_id = %(target_id)s
            ORDER BY bv.version_no DESC
            LIMIT 1
        )
        SELECT
            b.blueprint_id,
            b.blueprint_key,
            b.name AS target_name,
            b.description,
            sv.version_no,
            sv.status,
            sv.change_note,
            COUNT(bi.blueprint_item_id)::int AS module_count,
            COUNT(*) FILTER (WHERE COALESCE(bi.enabled, false))::int AS enabled_module_count,
            COALESCE(
                ARRAY_AGG(m.name ORDER BY bi.item_order)
                    FILTER (WHERE bi.blueprint_item_id IS NOT NULL),
                ARRAY[]::text[]
            ) AS module_names,
            sv.created_by,
            sv.updated_at
        FROM proc.blueprints b
        JOIN selected_version sv
            ON sv.blueprint_id = b.blueprint_id
        LEFT JOIN proc.blueprint_items bi
            ON bi.blueprint_version_id = sv.blueprint_version_id
        LEFT JOIN proc.module_versions mv
            ON mv.module_version_id = bi.module_version_id
        LEFT JOIN proc.modules m
            ON m.module_id = mv.module_id
        WHERE b.blueprint_id = %(target_id)s
        GROUP BY
            b.blueprint_id,
            b.blueprint_key,
            b.name,
            b.description,
            sv.version_no,
            sv.status,
            sv.change_note,
            sv.created_by,
            sv.updated_at;
    """

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                _ensure_history_table(cursor)
                cursor.execute(query, {"target_id": str(target_id)})
                row = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT
                        approval_status_history_id,
                        from_status,
                        to_status,
                        action_label,
                        changed_by,
                        changed_at,
                        note
                    FROM proc.approval_status_histories
                    WHERE
                        target_type = %(target_type)s
                        AND target_id = %(target_id)s
                    ORDER BY changed_at DESC, approval_status_history_id DESC;
                    """,
                    {
                        "target_type": APPROVAL_TARGET_TYPE,
                        "target_id": target_id,
                    },
                )
                history_rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError("Approval status detail query failed.") from exception

    if row is None:
        return None

    return ApprovalStatusDetailData(
        target_id=row[0],
        target_key=row[1],
        target_name=row[2],
        target_type=APPROVAL_TARGET_TYPE,
        version_no=row[4],
        status=row[5],
        status_label=SOURCE_DOC_STATUS_LABELS.get(row[5], row[5]),
        next_action=APPROVAL_NEXT_ACTIONS.get(row[5], "確認のみ"),
        module_count=row[7],
        enabled_module_count=row[8],
        module_names=list(row[9] or []),
        description=row[3],
        change_note=row[6],
        created_by=row[10],
        updated_at=_format_updated_at(row[11]),
        allowed_transitions=_build_transition_data(row[5]),
        history=_build_history_items(history_rows),
    )


def update_status(
    settings: AppSettings,
    target_id: int,
    to_status: str,
    changed_by: str | None = None,
    note: str | None = None,
) -> ApprovalStatusDetailData | None:
    """Update the latest approval status for one target."""

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
                _ensure_history_table(cursor)
                cursor.execute(
                    """
                    SELECT
                        bv.blueprint_version_id,
                        bv.status
                    FROM proc.blueprint_versions bv
                    WHERE bv.blueprint_id = %(target_id)s
                    ORDER BY bv.version_no DESC
                    LIMIT 1;
                    """,
                    {"target_id": target_id},
                )
                current_row = cursor.fetchone()
                if current_row is None:
                    return None

                blueprint_version_id = int(current_row[0])
                current_status = str(current_row[1])
                allowed_transitions = APPROVAL_ALLOWED_TRANSITIONS.get(current_status, [])
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
                    UPDATE proc.blueprint_versions
                    SET
                        status = %(to_status)s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE blueprint_version_id = %(blueprint_version_id)s;
                    """,
                    {
                        "to_status": to_status,
                        "blueprint_version_id": blueprint_version_id,
                    },
                )
                cursor.execute(
                    """
                    INSERT INTO proc.approval_status_histories (
                        target_type,
                        target_id,
                        target_version_id,
                        from_status,
                        to_status,
                        action_label,
                        changed_by,
                        note
                    )
                    VALUES (
                        %(target_type)s,
                        %(target_id)s,
                        %(target_version_id)s,
                        %(from_status)s,
                        %(to_status)s,
                        %(action_label)s,
                        %(changed_by)s,
                        %(note)s
                    );
                    """,
                    {
                        "target_type": APPROVAL_TARGET_TYPE,
                        "target_id": target_id,
                        "target_version_id": blueprint_version_id,
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
        raise DatabaseConnectionError("Approval status update failed.") from exception

    return get_status_detail(settings, target_id)
