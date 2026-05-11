"""Case document master and context resolution helpers.

The current implementation uses deterministic seed data that mirrors the
Access-derived column structure. The public functions are intentionally shaped
so the seed lookup can be replaced by an Access DB adapter later.
"""

from collections.abc import Iterable

from app.core.config import AppSettings
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

_DEVICE_VALUES = {
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

_COMMON_VALUES = {
    "operator_user": {
        "key": "USER",
        "value": "cs-operator",
        "source": "case_common_values.operator_user",
    }
}


def _as_option(value: str) -> CaseDocMasterOptionData:
    return CaseDocMasterOptionData(value=value, label=value)


def _unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _to_unit_config_item(row: dict[str, object]) -> CaseDocUnitConfigItemData:
    return CaseDocUnitConfigItemData(
        unit_config_id=str(row["unit_config_id"]),
        fs_cluster_name=str(row["fs_cluster_name"]),
        block=str(row["block"]),
        prefecture=str(row["prefecture"]),
        building=str(row["building"]),
    )


def list_case_doc_prefectures(settings: AppSettings) -> CaseDocMasterOptionsData:
    """Return prefectures available for case document generation."""

    del settings
    values = _unique_ordered(str(row["prefecture"]) for row in _UNIT_CONFIGS)
    return CaseDocMasterOptionsData(items=[_as_option(value) for value in values])


def list_case_doc_buildings(settings: AppSettings, prefecture: str) -> CaseDocMasterOptionsData:
    """Return buildings filtered by prefecture."""

    del settings
    values = _unique_ordered(
        str(row["building"])
        for row in _UNIT_CONFIGS
        if row["prefecture"] == prefecture
    )
    return CaseDocMasterOptionsData(items=[_as_option(value) for value in values])


def list_case_doc_unit_configs(
    settings: AppSettings,
    prefecture: str,
    building: str,
) -> CaseDocUnitConfigListData:
    """Return unit configuration candidates for selected location."""

    del settings
    items = [
        _to_unit_config_item(row)
        for row in _UNIT_CONFIGS
        if row["prefecture"] == prefecture and row["building"] == building
    ]
    return CaseDocUnitConfigListData(items=items)


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


def resolve_case_doc_context(
    settings: AppSettings,
    payload: CaseDocResolveContextRequest,
) -> CaseDocResolveContextData:
    """Resolve generation context without accepting manual placeholder values."""

    del settings
    unit_config = _find_unit_config(payload)
    hosts = unit_config["hosts"]
    if not isinstance(hosts, dict):
        raise ValueError("unit configuration hosts are invalid.")

    host_assignments = [
        CaseDocHostAssignmentData(
            slot_key=slot_key,
            device_type=str(host["device_type"]),
            system=str(host["system"]),
            host_name=str(host["host_name"]),
        )
        for slot_key, host in hosts.items()
        if isinstance(host, dict)
    ]

    common_values = [CaseDocCommonValueData(**value) for value in _COMMON_VALUES.values()]

    resolved_placeholders = [
        CaseDocResolvedPlaceholderData(
            placeholder="SBC_COMMAND_FLOATING_IP",
            value=device_values["command_floating_ip"],
            source_table="SBC",
            source_column="command_floating_ip",
            host_name=assignment.host_name,
        )
        for assignment in host_assignments
        if assignment.device_type == "SBC"
        if (device_values := _DEVICE_VALUES.get(assignment.host_name)) is not None
    ]
    resolved_placeholders.extend(
        CaseDocResolvedPlaceholderData(
            placeholder=value.key,
            value=value.value,
            source_table="case_common_values",
            source_column=value.key.lower(),
            host_name=None,
        )
        for value in common_values
    )

    return CaseDocResolveContextData(
        source_doc_id=payload.source_doc_id,
        unit_config=_to_unit_config_item(unit_config),
        host_assignments=host_assignments,
        common_values=common_values,
        resolved_placeholders=resolved_placeholders,
    )
