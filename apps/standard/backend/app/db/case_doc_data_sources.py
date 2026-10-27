"""Access exports are stored in one directory per source, including SSC."""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re

from psycopg.rows import dict_row
import psycopg
import yaml

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import CaseDocDataSourceData, CaseDocDataSourceListData, CaseDocDataSourceRequest
from app.db.case_doc_workflows import UNI_EXPORT_FILES, definition_path, read_workflow, workflow_path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS proc.case_doc_data_sources (
    source_id text PRIMARY KEY,
    name text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    description text NOT NULL DEFAULT '',
    updated_at timestamptz NOT NULL DEFAULT now()
);
UPDATE proc.case_doc_data_sources
SET source_id = 'ssc', name = CASE WHEN name = 'SBC' THEN 'SSC' ELSE name END
WHERE source_id = 'sbc';
DO $$
BEGIN
    IF to_regclass('proc.case_documents') IS NOT NULL THEN
        UPDATE proc.case_documents
        SET context_json = jsonb_set(context_json, '{data_source_id}', '"ssc"'::jsonb)
            || CASE WHEN COALESCE(NULLIF(context_json ->> 'data_source_name', ''), 'SBC') = 'SBC'
                    THEN '{"data_source_name":"SSC"}'::jsonb ELSE '{}'::jsonb END
        WHERE context_json ->> 'data_source_id' = 'sbc';
    END IF;
END $$;
INSERT INTO proc.case_doc_data_sources (source_id, name)
VALUES ('ssc', 'SSC') ON CONFLICT (source_id) DO NOTHING;
"""


def canonical_data_source_id(source_id: str | None) -> str:
    return "ssc" if not source_id or source_id == "sbc" else source_id


def _paths(settings: AppSettings, source_id: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,39}", source_id):
        raise ValueError("参照元DBの識別子が不正です。")
    if source_id == "sbc":
        raise ValueError("sbcは旧識別子です。既存の参照元DBにはsscを指定してください。")
    root = Path(settings.case_doc_access_export_dir).resolve()
    mapping = Path(settings.case_doc_placeholder_mapping_path).resolve()
    directory = root / source_id
    mapping_root = mapping.parent / "placeholder_mappings"
    mapping_path = mapping if source_id == "ssc" else mapping_root / (source_id + ".yml")
    if directory.resolve().parent != root or (
        source_id != "ssc" and mapping_path.resolve().parent != mapping_root.resolve()
    ):
        raise ValueError("参照元DBの配置先が不正です。")
    return directory, mapping_path


def _files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted((path for path in directory.iterdir() if path.is_file()
                   and not path.is_symlink() and not path.name.startswith("~$")
                   and path.suffix.lower() in {".xlsx", ".xlsm", ".csv"}), key=lambda p: p.name.casefold())


def _to_data(settings: AppSettings, row: dict) -> CaseDocDataSourceData:
    directory, _ = _paths(settings, row["source_id"])
    files = _files(directory)
    latest = max((path.stat().st_mtime for path in files), default=None)
    mode, message = "unit_config", ""
    ready = any(path.name.casefold() in {"ユニット構成.xlsx", "unit_config.xlsx"} for path in files)
    try:
        profile_path = workflow_path(settings.case_doc_placeholder_mapping_path, row["source_id"])
        profile = read_workflow(profile_path)
        mode = profile["mode"]
        if mode == "uni":
            missing = [name for name in UNI_EXPORT_FILES if not (directory / name).is_file()]
            ready = not missing and definition_path(profile_path, profile).is_file()
            message = "UNIの抽出ファイルが不足しています: " + "、".join(missing) if missing else (
                "" if ready else "UNIのビル別ホスト名規則が未配置です。")
        elif not ready:
            message = "選択した参照元DBにユニット構成.xlsxが配置されていません。"
    except (OSError, ValueError, yaml.YAMLError):
        ready, message = False, "参照元DBの案件化方式の設定を読み込めませんでした。"
    return CaseDocDataSourceData(
        **{key: row[key] for key in ("source_id", "name", "enabled", "description")},
        file_count=len(files), export_directory=str(directory),
        files_updated_at=datetime.fromtimestamp(latest, timezone.utc).isoformat() if latest else None,
        generation_ready=ready, generation_mode=mode, generation_message=message,
    )


def list_data_sources(settings: AppSettings, include_disabled: bool = False) -> CaseDocDataSourceListData:
    try:
        with psycopg.connect(settings.database_url, connect_timeout=settings.db_connect_timeout_seconds) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(SCHEMA_SQL)
                cursor.execute("SELECT source_id, name, enabled, description FROM proc.case_doc_data_sources WHERE enabled OR %s ORDER BY CASE WHEN source_id = 'ssc' THEN 0 ELSE 1 END, source_id", (include_disabled,))
                rows = cursor.fetchall()
    except psycopg.Error as exception:
        raise DatabaseConnectionError("参照元DB一覧の取得に失敗しました。") from exception
    return CaseDocDataSourceListData(items=[_to_data(settings, row) for row in rows])


def save_data_source(settings: AppSettings, payload: CaseDocDataSourceRequest, *, create: bool) -> CaseDocDataSourceData:
    name = payload.name.strip()
    if not name:
        raise ValueError("参照元DB名を入力してください。")
    if payload.source_id == "ssc" and not payload.enabled:
        raise ValueError("既存案件との互換性のためSSCは無効化できません。")
    directory, mapping = _paths(settings, payload.source_id)
    try:
        with psycopg.connect(settings.database_url, connect_timeout=settings.db_connect_timeout_seconds) as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(SCHEMA_SQL)
                values = {**payload.model_dump(), "name": name}
                if create:
                    cursor.execute("INSERT INTO proc.case_doc_data_sources (source_id, name, enabled, description) VALUES (%(source_id)s,%(name)s,%(enabled)s,%(description)s) RETURNING source_id, name, enabled, description", values)
                else:
                    cursor.execute("UPDATE proc.case_doc_data_sources SET name=%(name)s, enabled=%(enabled)s, description=%(description)s, updated_at=now() WHERE source_id=%(source_id)s RETURNING source_id, name, enabled, description", values)
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("参照元DBが見つかりません。")
                if create and payload.source_id != "ssc":
                    directory.mkdir(parents=True, exist_ok=True)
                    mapping.parent.mkdir(parents=True, exist_ok=True)
                    # A new namespace must never inherit another DB's definitions.
                    if not mapping.exists():
                        with mapping.open("x", encoding="utf-8") as file:
                            file.write("version: 1\nplaceholders: []\n")
    except psycopg.errors.UniqueViolation as exception:
        raise ValueError("この参照元DBの識別子はすでに登録されています。") from exception
    except psycopg.Error as exception:
        raise DatabaseConnectionError("参照元DBの保存に失敗しました。") from exception
    return _to_data(settings, row)


def select_data_source(settings: AppSettings, source_id: str | None) -> tuple[AppSettings, CaseDocDataSourceData | None]:
    if source_id is None:
        if settings.case_doc_master_source == "export_file":
            directory, _ = _paths(settings, "ssc")
            return settings.model_copy(update={"case_doc_access_export_dir": str(directory)}), None
        return settings, None
    source_id = canonical_data_source_id(source_id)
    if source_id != "ssc" and settings.case_doc_master_source != "export_file":
        raise ValueError("追加した参照元DBには抽出ファイル方式を使用してください。")
    _paths(settings, source_id)
    sources = list_data_sources(settings, include_disabled=True)
    source = next((item for item in sources.items if item.source_id == source_id), None)
    if source is None or not source.enabled:
        raise ValueError("選択した参照元DBは存在しないか、無効になっています。")
    directory, mapping = _paths(settings, source_id)
    if source_id != "ssc" and not mapping.is_file():
        raise ValueError("選択した参照元DBのプレースホルダ設定ファイルがありません。")
    return settings.model_copy(update={"case_doc_access_export_dir": str(directory), "case_doc_placeholder_mapping_path": str(mapping),
        "case_doc_generation_mode": source.generation_mode,
        "case_doc_workflow_path": str(workflow_path(settings.case_doc_placeholder_mapping_path, source_id))}), source


def data_source_revision(settings: AppSettings) -> str:
    digest = hashlib.sha256()
    files = _files(Path(settings.case_doc_access_export_dir))
    mapping = Path(settings.case_doc_placeholder_mapping_path)
    if mapping.is_file():
        files.append(mapping)
    if settings.case_doc_workflow_path:
        profile_path = Path(settings.case_doc_workflow_path)
        if profile_path.is_file():
            files.append(profile_path)
            profile = read_workflow(profile_path)
            if profile["mode"] == "uni":
                master = definition_path(profile_path, profile)
                if master.is_file():
                    files.append(master)
    for path in files:
        digest.update(path.name.encode("utf-8") + b"\0")
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()
