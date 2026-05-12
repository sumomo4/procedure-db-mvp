"""Case document master repositories.

The seed repository keeps the current deterministic data while the public
case_docs module owns repository selection.
"""

import csv
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from openpyxl import load_workbook

from app.core.responses import (
    CaseDocCommonValueData,
    CaseDocHostAssignmentData,
    CaseDocMasterOptionData,
    CaseDocMasterOptionsData,
    CaseDocResolvedPlaceholderData,
    CaseDocResolveContextData,
    CaseDocResolveContextRequest,
    CaseDocUnitConfigItemData,
    CaseDocUnitConfigListData,
)


def _u(value: str) -> str:
    """Decode escaped Japanese literals while keeping this source ASCII-safe."""

    return value.encode("ascii").decode("unicode_escape")


_UNIT_CONFIGS = [
    {
        "unit_config_id": "unit-tokyo-001",
        "fs_cluster_name": "FS-CL-TYO-01",
        "block": "B001",
        "prefecture": _u("\\u6771\\u4eac\\u90fd"),
        "building": _u("\\u54c1\\u5ddd\\u30d3\\u30eb"),
        "hosts": {
            "GUI_0": {"device_type": "GUI", "system": "0", "host_name": "gui-tyo-001-0"},
            "GUI_1": {"device_type": "GUI", "system": "1", "host_name": "gui-tyo-001-1"},
            "SBC_CL1_0": {"device_type": "SBC", "system": "0", "host_name": "sbc-tyo-cl1-0"},
            "SBC_CL1_1": {"device_type": "SBC", "system": "1", "host_name": "sbc-tyo-cl1-1"},
        },
    },
    {
        "unit_config_id": "unit-osaka-001",
        "fs_cluster_name": "FS-CL-OSA-01",
        "block": "B002",
        "prefecture": _u("\\u5927\\u962a\\u5e9c"),
        "building": _u("\\u5802\\u5cf6\\u30d3\\u30eb"),
        "hosts": {
            "GUI_0": {"device_type": "GUI", "system": "0", "host_name": "gui-osa-001-0"},
            "GUI_1": {"device_type": "GUI", "system": "1", "host_name": "gui-osa-001-1"},
            "SBC_CL1_0": {"device_type": "SBC", "system": "0", "host_name": "sbc-osa-cl1-0"},
            "SBC_CL1_1": {"device_type": "SBC", "system": "1", "host_name": "sbc-osa-cl1-1"},
        },
    },
]

_DEVICE_VALUES_BY_HOST_NAME = {
    "sbc-tyo-cl1-0": {
        "command_floating_ip": "10.10.1.10",
        "tts_host": "tts-tyo-01",
        "tts_ip": "10.10.1.200",
        "tts_port": "23",
    },
    "sbc-tyo-cl1-1": {
        "command_floating_ip": "10.10.1.11",
        "tts_host": "tts-tyo-01",
        "tts_ip": "10.10.1.200",
        "tts_port": "23",
    },
    "sbc-osa-cl1-0": {
        "command_floating_ip": "10.20.1.10",
        "tts_host": "tts-osa-01",
        "tts_ip": "10.20.1.200",
        "tts_port": "23",
    },
    "sbc-osa-cl1-1": {
        "command_floating_ip": "10.20.1.11",
        "tts_host": "tts-osa-01",
        "tts_ip": "10.20.1.200",
        "tts_port": "23",
    },
}

_COMMON_VALUE_SOURCE_TABLE = "case_common_values"
_COMMON_VALUE_DEFINITIONS = [
    {
        "key": "LOGIN_USER",
        "value": "cs-operator",
        "source_table": _COMMON_VALUE_SOURCE_TABLE,
        "source_column": "login_user",
    }
]

UNIT_CONFIG_FILE_NAMES = ("unit_config.xlsx", _u(r"\u30e6\u30cb\u30c3\u30c8\u69cb\u6210.xlsx"))
SBC_FILE_NAMES = ("SBC.xlsx", "sbc.xlsx")
COMMON_VALUES_XLSX_FILE_NAME = "case_common_values.xlsx"
COMMON_VALUES_CSV_FILE_NAME = "case_common_values.csv"

UNIT_CONFIG_COLUMN_ALIASES = {
    "unit_config_id": ("unit_config_id", _u(r"\u30e6\u30cb\u30c3\u30c8\u69cb\u6210ID")),
    "fs_cluster_name": ("fs_cluster_name", "FS" + _u(r"\u30af\u30e9\u30b9\u30bf\u540d")),
    "block": ("block", _u(r"\u30d6\u30ed\u30c3\u30af")),
    "prefecture": (
        "prefecture",
        _u(r"\u90fd\u9053\u5e9c\u770c"),
        _u(r"\u88c5\u7f6e\u8a2d\u7f6e\u90fd\u9053\u5e9c\u770c"),
        _u(r"\u88c5\u7f6e\u8a2d\u7f6e\u5e9c\u770c"),
    ),
    "building": ("building", _u(r"\u30d3\u30eb"), _u(r"\u88c5\u7f6e\u8a2d\u7f6e\u30d3\u30eb")),
}
SBC_COLUMN_ALIASES = {
    "host_name": ("host_name", _u(r"\u30db\u30b9\u30c8\u540d")),
    "command_floating_ip": (
        "command_floating_ip",
        _u(r"\u30b3\u30de\u30f3\u30c9\u7528\u30d5\u30ed\u30fc\u30c6\u30a3\u30f3\u30b0IP\u30a2\u30c9\u30ec\u30b9"),
    ),
    "tts_host": ("tts_host", "TTS-Host"),
    "tts_ip": ("tts_ip", "TTS-IP"),
    "tts_port": ("tts_port", "TTS-Port"),
}
# TTS placeholders are MVP-provisional names based on the UNISBC Access export files.
SBC_PLACEHOLDER_DEFINITIONS = (
    ("SBC_COMMAND_FLOATING_IP", "command_floating_ip", "command_floating_ip"),
    ("TTS_HOST", "tts_host", "tts_host"),
    ("TTS_IP", "tts_ip", "tts_ip"),
    ("TTS_PORT", "tts_port", "tts_port"),
)
COMMON_VALUE_COLUMN_ALIASES = {
    "key": ("key", _u(r"\u30ad\u30fc")),
    "value": ("value", _u(r"\u5024")),
    "source_table": ("source_table", _u(r"\u51fa\u5178\u30c6\u30fc\u30d6\u30eb")),
    "source_column": ("source_column", _u(r"\u51fa\u5178\u30ab\u30e9\u30e0")),
}
DEVICE_SLOT_SUFFIX = _u(r"\u7cfb")


def _normalize_key(value: str) -> str:
    return re.sub(r"[\s\u3000]+", "", value).lower()


def _resolve_export_file_path(export_dir: Path, file_names: Iterable[str]) -> Path:
    for file_name in file_names:
        path = export_dir / file_name
        if path.exists():
            return path
    expected = ", ".join(file_names)
    raise ValueError(f"case document export file was not found: {expected}")


def _cell_to_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _read_xlsx_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ValueError(f"case document export file was not found: {path.name}")

    workbook = load_workbook(path, data_only=True, read_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    header_index = next((index for index, row in enumerate(rows) if any(_cell_to_text(value) for value in row)), None)
    if header_index is None:
        return []

    headers = [_normalize_key(_cell_to_text(value)) for value in rows[header_index]]
    records: list[dict[str, str]] = []
    for row in rows[header_index + 1 :]:
        record = {header: _cell_to_text(value) for header, value in zip(headers, row, strict=False) if header}
        if any(record.values()):
            records.append(record)
    return records


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ValueError(f"case document export file was not found: {path.name}")

    with path.open(encoding="utf-8-sig", newline="") as file:
        return [
            {_normalize_key(str(key)): _cell_to_text(value) for key, value in row.items() if key}
            for row in csv.DictReader(file)
            if any(_cell_to_text(value) for value in row.values())
        ]


def _value_from_aliases(row: dict[str, str], aliases: Iterable[str], field_name: str) -> str:
    for alias in aliases:
        value = row.get(_normalize_key(alias), "").strip()
        if value:
            return value
    raise ValueError(f"required column value was not found: {field_name}")


def _optional_value_from_aliases(row: dict[str, str], aliases: Iterable[str]) -> str:
    for alias in aliases:
        value = row.get(_normalize_key(alias), "").strip()
        if value:
            return value
    return ""


def _slot_key_from_column_name(column_name: str) -> str | None:
    ignored_columns = {_normalize_key(alias) for aliases in UNIT_CONFIG_COLUMN_ALIASES.values() for alias in aliases}
    if column_name in ignored_columns:
        return None
    normalized_suffix = _normalize_key(DEVICE_SLOT_SUFFIX)
    if not column_name.endswith(normalized_suffix):
        return None
    slot_key = column_name.removesuffix(normalized_suffix).strip().upper()
    return slot_key or None


def _as_option(value: str) -> CaseDocMasterOptionData:
    return CaseDocMasterOptionData(value=value, label=value)


def _unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered


def _sort_unit_configs(unit_configs: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        unit_configs,
        key=lambda row: (
            str(row["prefecture"]),
            str(row["building"]),
            str(row["fs_cluster_name"]),
            str(row["block"]),
            str(row["unit_config_id"]),
        ),
    )


def _to_unit_config_item(row: dict[str, object]) -> CaseDocUnitConfigItemData:
    return CaseDocUnitConfigItemData(
        unit_config_id=str(row["unit_config_id"]),
        fs_cluster_name=str(row["fs_cluster_name"]),
        block=str(row["block"]),
        prefecture=str(row["prefecture"]),
        building=str(row["building"]),
    )


def _find_unit_config(payload: CaseDocResolveContextRequest) -> dict[str, object]:
    candidates = [
        row
        for row in _UNIT_CONFIGS
        if row["prefecture"] == payload.prefecture and row["building"] == payload.building
    ]

    if payload.unit_config_id:
        candidates = [row for row in candidates if row["unit_config_id"] == payload.unit_config_id]
    if payload.fs_cluster_name:
        candidates = [row for row in candidates if row["fs_cluster_name"] == payload.fs_cluster_name]
    if payload.block:
        candidates = [row for row in candidates if row["block"] == payload.block]

    if not candidates:
        raise ValueError("unit configuration was not found.")
    return candidates[0]


def _select_target_host_assignment(
    host_assignments: list[CaseDocHostAssignmentData],
    target_slot_key: str | None,
) -> CaseDocHostAssignmentData:
    """Select the target SBC host assignment used as the document value key."""

    sbc_assignments = [assignment for assignment in host_assignments if assignment.device_type == "SBC"]
    if target_slot_key:
        for assignment in sbc_assignments:
            if assignment.slot_key == target_slot_key:
                return assignment
        raise ValueError("target SBC slot was not found.")

    if not sbc_assignments:
        raise ValueError("target SBC slot was not found.")
    return sbc_assignments[0]


def _to_host_assignments(hosts: dict[str, object]) -> list[CaseDocHostAssignmentData]:
    return [
        CaseDocHostAssignmentData(
            slot_key=slot_key,
            device_type=str(host["device_type"]),
            system=str(host["system"]),
            host_name=str(host["host_name"]),
        )
        for slot_key, host in hosts.items()
        if isinstance(host, dict)
    ]


def _list_common_values() -> list[CaseDocCommonValueData]:
    return [
        CaseDocCommonValueData(
            **value,
            source=f"{value['source_table']}.{value['source_column']}",
        )
        for value in _COMMON_VALUE_DEFINITIONS
    ]


def _resolve_sbc_placeholders_by_host_name(
    host_assignments: list[CaseDocHostAssignmentData],
) -> list[CaseDocResolvedPlaceholderData]:
    """Resolve SBC values by using each assignment host name as the master key."""

    return _resolve_sbc_placeholders_from_values(host_assignments, _DEVICE_VALUES_BY_HOST_NAME)


def _resolve_sbc_placeholders_from_values(
    host_assignments: list[CaseDocHostAssignmentData],
    device_values_by_host_name: dict[str, dict[str, str]],
) -> list[CaseDocResolvedPlaceholderData]:
    resolved_placeholders: list[CaseDocResolvedPlaceholderData] = []
    for assignment in host_assignments:
        if assignment.device_type != "SBC":
            continue

        device_values = device_values_by_host_name.get(assignment.host_name)
        if device_values is None:
            continue

        for placeholder, value_key, source_column in SBC_PLACEHOLDER_DEFINITIONS:
            value = device_values.get(value_key)
            if not value:
                continue
            resolved_placeholders.append(
                CaseDocResolvedPlaceholderData(
                    placeholder=placeholder,
                    value=value,
                    source_table="SBC",
                    source_column=source_column,
                    host_name=assignment.host_name,
                )
            )
    return resolved_placeholders


def _resolve_common_placeholders(
    common_values: list[CaseDocCommonValueData],
) -> list[CaseDocResolvedPlaceholderData]:
    return [
        CaseDocResolvedPlaceholderData(
            placeholder=value.key,
            value=value.value,
            source_table=value.source_table,
            source_column=value.source_column,
            host_name=None,
        )
        for value in common_values
    ]


class CaseDocMasterRepository(Protocol):
    """Repository boundary for case document master data."""

    def list_prefectures(self) -> CaseDocMasterOptionsData:
        """Return prefectures available for case document generation."""

    def list_buildings(self, prefecture: str) -> CaseDocMasterOptionsData:
        """Return buildings filtered by prefecture."""

    def list_unit_configs(self, prefecture: str, building: str) -> CaseDocUnitConfigListData:
        """Return unit configuration candidates for selected location."""

    def resolve_context(self, payload: CaseDocResolveContextRequest) -> CaseDocResolveContextData:
        """Resolve generation context from repository data."""


class SeedCaseDocMasterRepository:
    """Deterministic case document master data used before Access export import."""

    def list_prefectures(self) -> CaseDocMasterOptionsData:
        values = _unique_ordered(str(row["prefecture"]) for row in _UNIT_CONFIGS)
        return CaseDocMasterOptionsData(items=[_as_option(value) for value in values])

    def list_buildings(self, prefecture: str) -> CaseDocMasterOptionsData:
        values = _unique_ordered(
            str(row["building"])
            for row in _UNIT_CONFIGS
            if row["prefecture"] == prefecture
        )
        return CaseDocMasterOptionsData(items=[_as_option(value) for value in values])

    def list_unit_configs(self, prefecture: str, building: str) -> CaseDocUnitConfigListData:
        items = [
            _to_unit_config_item(row)
            for row in _UNIT_CONFIGS
            if row["prefecture"] == prefecture and row["building"] == building
        ]
        return CaseDocUnitConfigListData(items=items)

    def resolve_context(self, payload: CaseDocResolveContextRequest) -> CaseDocResolveContextData:
        unit_config = _find_unit_config(payload)
        hosts = unit_config["hosts"]
        if not isinstance(hosts, dict):
            raise ValueError("unit configuration hosts are invalid.")

        host_assignments = _to_host_assignments(hosts)
        target_assignment = _select_target_host_assignment(host_assignments, payload.target_slot_key)
        common_values = _list_common_values()
        resolved_placeholders = [
            *_resolve_sbc_placeholders_by_host_name(host_assignments),
            *_resolve_common_placeholders(common_values),
        ]

        return CaseDocResolveContextData(
            source_doc_id=payload.source_doc_id,
            unit_config=_to_unit_config_item(unit_config),
            target_assignment=target_assignment,
            host_assignments=host_assignments,
            common_values=common_values,
            resolved_placeholders=resolved_placeholders,
        )

class ExportFileCaseDocMasterRepository:
    """Case document master data loaded from Access-derived export files."""

    def __init__(self, export_dir: str) -> None:
        self.export_dir = Path(export_dir)

    def list_prefectures(self) -> CaseDocMasterOptionsData:
        values = sorted(_unique_ordered(str(row["prefecture"]) for row in self._load_unit_configs()))
        return CaseDocMasterOptionsData(items=[_as_option(value) for value in values])

    def list_buildings(self, prefecture: str) -> CaseDocMasterOptionsData:
        values = sorted(
            _unique_ordered(
                str(row["building"])
                for row in self._load_unit_configs()
                if row["prefecture"] == prefecture
            )
        )
        return CaseDocMasterOptionsData(items=[_as_option(value) for value in values])

    def list_unit_configs(self, prefecture: str, building: str) -> CaseDocUnitConfigListData:
        items = [
            _to_unit_config_item(row)
            for row in _sort_unit_configs(self._load_unit_configs())
            if row["prefecture"] == prefecture and row["building"] == building
        ]
        return CaseDocUnitConfigListData(items=items)

    def resolve_context(self, payload: CaseDocResolveContextRequest) -> CaseDocResolveContextData:
        unit_config = self._find_unit_config(payload)
        hosts = unit_config["hosts"]
        if not isinstance(hosts, dict):
            raise ValueError("unit configuration hosts are invalid.")

        host_assignments = _to_host_assignments(hosts)
        target_assignment = _select_target_host_assignment(host_assignments, payload.target_slot_key)
        common_values = self._load_common_values()
        resolved_placeholders = [
            *self._resolve_sbc_placeholders_by_host_name(host_assignments),
            *_resolve_common_placeholders(common_values),
        ]

        return CaseDocResolveContextData(
            source_doc_id=payload.source_doc_id,
            unit_config=_to_unit_config_item(unit_config),
            target_assignment=target_assignment,
            host_assignments=host_assignments,
            common_values=common_values,
            resolved_placeholders=resolved_placeholders,
        )

    def _find_unit_config(self, payload: CaseDocResolveContextRequest) -> dict[str, object]:
        candidates = [
            row
            for row in self._load_unit_configs()
            if row["prefecture"] == payload.prefecture and row["building"] == payload.building
        ]

        if payload.unit_config_id:
            candidates = [row for row in candidates if row["unit_config_id"] == payload.unit_config_id]
        if payload.fs_cluster_name:
            candidates = [row for row in candidates if row["fs_cluster_name"] == payload.fs_cluster_name]
        if payload.block:
            candidates = [row for row in candidates if row["block"] == payload.block]

        if not candidates:
            raise ValueError("unit configuration was not found.")
        return candidates[0]

    def _load_unit_configs(self) -> list[dict[str, object]]:
        rows = _read_xlsx_rows(_resolve_export_file_path(self.export_dir, UNIT_CONFIG_FILE_NAMES))
        unit_configs: list[dict[str, object]] = []
        for index, row in enumerate(rows, start=1):
            fs_cluster_name = _value_from_aliases(row, UNIT_CONFIG_COLUMN_ALIASES["fs_cluster_name"], "fs_cluster_name")
            block = _value_from_aliases(row, UNIT_CONFIG_COLUMN_ALIASES["block"], "block")
            unit_config_id = _optional_value_from_aliases(row, UNIT_CONFIG_COLUMN_ALIASES["unit_config_id"])
            if not unit_config_id:
                unit_config_id = f"unit-export-{index}"

            hosts = {
                slot_key: {
                    "device_type": slot_key.split("_", 1)[0],
                    "system": slot_key.rsplit("_", 1)[-1] if "_" in slot_key else None,
                    "host_name": host_name,
                }
                for column_name, host_name in row.items()
                if (slot_key := _slot_key_from_column_name(column_name)) is not None
                if host_name
            }

            unit_configs.append(
                {
                    "unit_config_id": unit_config_id,
                    "fs_cluster_name": fs_cluster_name,
                    "block": block,
                    "prefecture": _value_from_aliases(row, UNIT_CONFIG_COLUMN_ALIASES["prefecture"], "prefecture"),
                    "building": _value_from_aliases(row, UNIT_CONFIG_COLUMN_ALIASES["building"], "building"),
                    "hosts": hosts,
                }
            )
        return unit_configs

    def _load_sbc_values_by_host_name(self) -> dict[str, dict[str, str]]:
        rows = _read_xlsx_rows(_resolve_export_file_path(self.export_dir, SBC_FILE_NAMES))
        values_by_host_name: dict[str, dict[str, str]] = {}
        for row in rows:
            host_name = _value_from_aliases(row, SBC_COLUMN_ALIASES["host_name"], "host_name")
            device_values = {
                "command_floating_ip": _value_from_aliases(
                    row,
                    SBC_COLUMN_ALIASES["command_floating_ip"],
                    "command_floating_ip",
                )
            }
            for value_key in ("tts_host", "tts_ip", "tts_port"):
                value = _optional_value_from_aliases(row, SBC_COLUMN_ALIASES[value_key])
                if value:
                    device_values[value_key] = value
            values_by_host_name[host_name] = device_values
        return values_by_host_name

    def _load_common_values(self) -> list[CaseDocCommonValueData]:
        xlsx_path = self.export_dir / COMMON_VALUES_XLSX_FILE_NAME
        csv_path = self.export_dir / COMMON_VALUES_CSV_FILE_NAME
        if xlsx_path.exists():
            rows = _read_xlsx_rows(xlsx_path)
        elif csv_path.exists():
            rows = _read_csv_rows(csv_path)
        else:
            return _list_common_values()

        common_values: list[CaseDocCommonValueData] = []
        for row in rows:
            key = _value_from_aliases(row, COMMON_VALUE_COLUMN_ALIASES["key"], "key")
            value = _value_from_aliases(row, COMMON_VALUE_COLUMN_ALIASES["value"], "value")
            source_table = _optional_value_from_aliases(row, COMMON_VALUE_COLUMN_ALIASES["source_table"]) or _COMMON_VALUE_SOURCE_TABLE
            source_column = _optional_value_from_aliases(row, COMMON_VALUE_COLUMN_ALIASES["source_column"]) or key.lower()
            common_values.append(
                CaseDocCommonValueData(
                    key=key,
                    value=value,
                    source_table=source_table,
                    source_column=source_column,
                    source=f"{source_table}.{source_column}",
                )
            )
        return common_values

    def _resolve_sbc_placeholders_by_host_name(
        self,
        host_assignments: list[CaseDocHostAssignmentData],
    ) -> list[CaseDocResolvedPlaceholderData]:
        return _resolve_sbc_placeholders_from_values(host_assignments, self._load_sbc_values_by_host_name())
