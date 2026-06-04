from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml
from openpyxl import Workbook


DEFAULT_DRIVER = "Microsoft Access Driver (*.mdb, *.accdb)"
DEFAULT_CONFIG_PATH = Path(__file__).with_name("access_export_config.yml")


@dataclass(frozen=True)
class ExportDefinition:
    name: str
    output_file: str
    sheet_name: str
    access_table: str | None = None
    sql: str | None = None


@dataclass(frozen=True)
class ExportResult:
    name: str
    output_file: str
    table_or_sql: str
    row_count: int
    column_count: int


def load_export_definitions(config_path: Path) -> list[ExportDefinition]:
    if not config_path.exists():
        raise FileNotFoundError(f"config file was not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file) or {}

    raw_exports = raw_config.get("exports")
    if not isinstance(raw_exports, list) or not raw_exports:
        raise ValueError("config must contain non-empty 'exports' list.")

    definitions: list[ExportDefinition] = []
    for index, raw_export in enumerate(raw_exports, start=1):
        if not isinstance(raw_export, dict):
            raise ValueError(f"exports[{index}] must be an object.")

        name = str(raw_export.get("name") or "").strip()
        access_table = str(raw_export.get("access_table") or "").strip() or None
        sql = str(raw_export.get("sql") or "").strip() or None
        output_file = str(raw_export.get("output_file") or "").strip()
        sheet_name = str(raw_export.get("sheet_name") or name or "export").strip()

        if not name:
            raise ValueError(f"exports[{index}].name is required.")
        if not output_file:
            raise ValueError(f"exports[{index}].output_file is required.")
        if bool(access_table) == bool(sql):
            raise ValueError(f"exports[{index}] must define exactly one of access_table or sql.")
        if Path(output_file).name != output_file:
            raise ValueError(f"exports[{index}].output_file must be a file name, not a path.")

        definitions.append(
            ExportDefinition(
                name=name,
                access_table=access_table,
                sql=sql,
                output_file=output_file,
                sheet_name=sheet_name[:31] or "export",
            )
        )

    return definitions


def build_access_connection_string(db_path: Path, driver: str) -> str:
    return f"DRIVER={{{driver}}};DBQ={db_path};"


def quote_access_identifier(identifier: str) -> str:
    escaped = identifier.replace("]", "]]")
    return f"[{escaped}]"


def build_select_sql(definition: ExportDefinition) -> str:
    if definition.sql:
        return definition.sql
    if not definition.access_table:
        raise ValueError(f"{definition.name}: access_table is required.")
    return f"SELECT * FROM {quote_access_identifier(definition.access_table)}"


def normalize_cell_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    return value


def write_rows_to_workbook(output_path: Path, sheet_name: str, columns: Sequence[str], rows: Iterable[Sequence[Any]]) -> int:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(list(columns))

    row_count = 0
    for row in rows:
        worksheet.append([normalize_cell_value(value) for value in row])
        row_count += 1

    workbook.save(output_path)
    return row_count


def backup_existing_outputs(output_dir: Path, output_files: Sequence[str]) -> Path | None:
    existing_files = [output_dir / file_name for file_name in output_files if (output_dir / file_name).exists()]
    if not existing_files:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = output_dir / "backup" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    for source_path in existing_files:
        shutil.copy2(source_path, backup_dir / source_path.name)

    manifest_path = output_dir / "export_manifest.json"
    if manifest_path.exists():
        shutil.copy2(manifest_path, backup_dir / manifest_path.name)

    return backup_dir


def connect_access(db_path: Path, driver: str):
    try:
        import pyodbc  # type: ignore[import-not-found]
    except ImportError as exception:
        raise RuntimeError("pyodbc is not installed. Run: python -m pip install -r requirements.txt") from exception

    connection_string = build_access_connection_string(db_path, driver)
    return pyodbc.connect(connection_string)


def export_definitions(
    db_path: Path,
    output_dir: Path,
    definitions: Sequence[ExportDefinition],
    driver: str,
    create_backup: bool,
) -> list[ExportResult]:
    if not db_path.exists():
        raise FileNotFoundError(f"AccessDB file was not found: {db_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    if create_backup:
        backup_dir = backup_existing_outputs(output_dir, [definition.output_file for definition in definitions])
        if backup_dir is not None:
            print(f"Backed up existing exports to: {backup_dir}")

    results: list[ExportResult] = []
    with connect_access(db_path, driver) as connection:
        for definition in definitions:
            sql = build_select_sql(definition)
            print(f"Exporting {definition.name}: {sql}")
            cursor = connection.cursor()
            cursor.execute(sql)
            columns = [column[0] for column in cursor.description or []]
            if not columns:
                raise ValueError(f"{definition.name}: query returned no columns.")

            output_path = output_dir / definition.output_file
            row_count = write_rows_to_workbook(output_path, definition.sheet_name, columns, cursor)
            if row_count == 0:
                print(f"Warning: {definition.name} exported 0 rows.", file=sys.stderr)

            results.append(
                ExportResult(
                    name=definition.name,
                    output_file=definition.output_file,
                    table_or_sql=definition.access_table or definition.sql or "",
                    row_count=row_count,
                    column_count=len(columns),
                )
            )
            print(f"Exported {definition.output_file}: {row_count} rows, {len(columns)} columns")

    return results


def write_manifest(output_dir: Path, db_path: Path, driver: str, results: Sequence[ExportResult]) -> Path:
    manifest = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db_path),
        "driver": driver,
        "output_dir": str(output_dir),
        "files": [
            {
                "name": result.name,
                "output_file": result.output_file,
                "source": result.table_or_sql,
                "row_count": result.row_count,
                "column_count": result.column_count,
            }
            for result in results
        ],
    }

    manifest_path = output_dir / "export_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export AccessDB tables to Excel files for procedure-db MVP.")
    parser.add_argument("--db", required=True, type=Path, help="Path to .accdb or .mdb file.")
    parser.add_argument("--out", required=True, type=Path, help="Output directory for exported .xlsx files.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Export config YAML path.")
    parser.add_argument("--driver", default=DEFAULT_DRIVER, help="ODBC driver name.")
    parser.add_argument("--no-backup", action="store_true", help="Overwrite existing exports without creating backup copies.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        definitions = load_export_definitions(args.config)
        results = export_definitions(
            db_path=args.db,
            output_dir=args.out,
            definitions=definitions,
            driver=args.driver,
            create_backup=not args.no_backup,
        )
        manifest_path = write_manifest(args.out, args.db, args.driver, results)
    except Exception as exception:
        print(f"Access export failed: {exception}", file=sys.stderr)
        return 1

    print(f"Export completed. Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
