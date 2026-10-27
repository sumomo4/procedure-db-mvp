"""Read-only samples using the production resolver with one transient definition."""

from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from app.core.case_doc_generation import _build_placeholder_values_for_assignment
from app.core.config import AppSettings
from app.core.responses import (
    CaseDocPlaceholderSampleData,
    CaseDocPlaceholderSampleOptionsData,
    CaseDocPlaceholderSampleRequest,
    CaseDocPlaceholderSampleUnitData,
    CaseDocPlaceholderMappingItemData,
    CaseDocResolveContextRequest,
)
from app.db.case_doc_repositories import (
    COMMON_VALUES_CSV_FILE_NAME,
    COMMON_VALUES_XLSX_FILE_NAME,
    SBC_COLUMN_ALIASES,
    UNIT_CONFIG_FILE_NAMES,
    ExportFileCaseDocMasterRepository,
    _normalize_key,
    _optional_value_from_aliases,
    _read_placeholder_source_table,
    _resolve_export_file_path,
    _sort_unit_configs,
    _source_slot_key_for_mapping,
    _to_host_assignments,
    _to_placeholder_mapping_item,
    _to_unit_config_item,
    _validate_placeholder_mapping_item,
)


class _SampleRepository(ExportFileCaseDocMasterRepository):
    def __init__(self, settings: AppSettings, mapping: CaseDocPlaceholderMappingItemData | None = None) -> None:
        super().__init__(settings.case_doc_access_export_dir, settings.case_doc_placeholder_mapping_path)
        self.mapping = mapping

    def _load_placeholder_mappings(self) -> list[CaseDocPlaceholderMappingItemData]:
        # Never initialize or modify the configured YAML file during a sample.
        return [self.mapping] if self.mapping is not None else []


def _repository(settings: AppSettings) -> _SampleRepository:
    if settings.case_doc_master_source != "export_file":
        raise ValueError("Placeholder samples require export_file master data.")
    if settings.case_doc_generation_mode == "uni":
        raise ValueError("UNIではtargetごとの対象工事を指定して置換結果を確認してください。")
    return _SampleRepository(settings)


def list_placeholder_sample_options(settings: AppSettings) -> CaseDocPlaceholderSampleOptionsData:
    repository = _repository(settings)
    return CaseDocPlaceholderSampleOptionsData(items=[
        CaseDocPlaceholderSampleUnitData(
            unit_config=_to_unit_config_item(unit),
            devices=_to_host_assignments(unit["hosts"]),
        )
        for unit in _sort_unit_configs(repository._load_unit_configs())
    ])


def _safe_source_path(export_dir: Path, name: str) -> Path:
    if not name or any(character in name for character in "/\\:") or Path(name).name != name:
        raise ValueError("Invalid placeholder source filename.")
    path = (export_dir / name).resolve()
    if path.parent != export_dir.resolve() or path.suffix.lower() not in {".xlsx", ".xlsm", ".csv"}:
        raise ValueError("Invalid placeholder source path.")
    return path


def preview_placeholder_sample(settings: AppSettings, payload: CaseDocPlaceholderSampleRequest) -> CaseDocPlaceholderSampleData:
    repository = _repository(settings)
    mapping = _to_placeholder_mapping_item(payload.mapping)
    _safe_source_path(repository.export_dir, mapping.source_file)
    _validate_placeholder_mapping_item(mapping)
    repository.mapping = mapping
    token = "{{" + mapping.name + "}}"
    result = CaseDocPlaceholderSampleData(status="unresolved", before=token, after=token)
    # Source documents are not accessed by resolve_context; only master data is used.
    selection = CaseDocResolveContextRequest(
        source_doc_id=1, prefecture=payload.prefecture, building=payload.building,
        unit_config_id=payload.unit_config_id, target_slot_key=payload.target_slot_key,
    )
    unit = repository._find_unit_config(selection)
    assignments = _to_host_assignments(unit["hosts"])
    target = next((item for item in assignments if item.slot_key == payload.target_slot_key), None)
    if mapping.scope == "device" and target is None:
        raise ValueError("Select a device belonging to the sample unit.")
    if payload.target_slot_key and target is None:
        raise ValueError("Sample device was not found in the selected unit.")
    if not mapping.enabled:
        result.status = "disabled"
        context = repository.resolve_context(selection)
        values = _build_placeholder_values_for_assignment(context, target or context.target_assignment)
        if mapping.name in values:
            result.status, result.after, result.uses_default = "resolved", values[mapping.name], True
        return result
    if mapping.scope == "device" and target.device_type != mapping.device_type:
        result.status = "not_applicable"
        return result

    source_assignment = target
    if mapping.scope == "device":
        source_slot = _source_slot_key_for_mapping(target, mapping)
        source_assignment = next((item for item in assignments if item.slot_key == source_slot), None)
        if source_assignment is None:
            result.status = "reference_missing"
            return result
        source_path = _safe_source_path(repository.export_dir, mapping.source_file)
        result.lookup_value = source_assignment.host_name
    elif mapping.scope == "unit":
        source_path = _resolve_export_file_path(repository.export_dir, UNIT_CONFIG_FILE_NAMES)
    else:
        candidates = [repository.export_dir / COMMON_VALUES_XLSX_FILE_NAME, repository.export_dir / COMMON_VALUES_CSV_FILE_NAME]
        source_path = next((path for path in candidates if path.is_file()), None)
        result.lookup_value = mapping.key_value

    trace_status = "lookup_mismatch"
    if source_path is not None:
        source_path = _safe_source_path(repository.export_dir, source_path.name)
        result.source_file = source_path.name
        if not source_path.is_file():
            result.status = "source_error"
            return result
        try:
            table = _read_placeholder_source_table(source_path)
        except (OSError, ValueError, InvalidFileException, BadZipFile):
            result.status = "source_error"
            return result
        result.sheet_name = table.sheet_name
        columns = {_normalize_key(column): column for column in table.columns}
        value_aliases = (mapping.value_column,) if mapping.scope == "unit" else (
            mapping.value_column, "value" if mapping.scope == "common" else mapping.source_column,
        )
        result.value_column = next((columns[_normalize_key(alias)] for alias in value_aliases if _normalize_key(alias) in columns), None)
        if mapping.scope == "unit":
            index = repository._load_unit_configs().index(unit)
            matching_rows = [table.rows[index]]
        else:
            key = _normalize_key(mapping.key_column)
            aliases = SBC_COLUMN_ALIASES["host_name"] if mapping.scope == "device" else ("key",)
            matching_rows = []
            for row in table.rows:
                if mapping.scope == "device" and key in row.lookup:
                    lookup = row.lookup[key]
                elif mapping.scope == "device" and key not in {_normalize_key(alias) for alias in aliases}:
                    lookup = ""
                else:
                    lookup = _optional_value_from_aliases(row.lookup, (mapping.key_column, *aliases))
                if lookup == result.lookup_value:
                    matching_rows.append(row)
            allow_aliases = mapping.scope == "common" or key in {_normalize_key(alias) for alias in aliases}
            result.key_column = columns.get(key) or (next((
                columns[_normalize_key(alias)] for alias in aliases if _normalize_key(alias) in columns
            ), None) if allow_aliases else None)
            if result.key_column is None:
                trace_status = "missing_column"
        if result.value_column is None:
            trace_status = "missing_column"
        elif matching_rows:
            nonempty_rows = [row for row in matching_rows if _optional_value_from_aliases(row.lookup, value_aliases)]
            row = nonempty_rows[-1] if mapping.scope == "device" and nonempty_rows else matching_rows[0]
            result.row_number = row.row_number
            trace_status = "unresolved" if _optional_value_from_aliases(row.lookup, value_aliases) else "empty_value"
            result.value_column = next((
                columns[_normalize_key(alias)] for alias in value_aliases
                if row.lookup.get(_normalize_key(alias)) and _normalize_key(alias) in columns
            ), result.value_column)

    try:
        context = repository.resolve_context(selection)
        values = _build_placeholder_values_for_assignment(context, target or context.target_assignment)
    except (OSError, ValueError, InvalidFileException, BadZipFile):
        result.status = trace_status if trace_status in {"empty_value", "missing_column"} else "source_error"
        return result
    if mapping.name in values:
        result.status = "resolved"
        result.after = values[mapping.name]
        result.uses_default = mapping.scope == "common" and result.row_number is None
    else:
        result.status = trace_status if mapping.scope != "common" or mapping.key_value == mapping.name else "unresolved"
    return result
