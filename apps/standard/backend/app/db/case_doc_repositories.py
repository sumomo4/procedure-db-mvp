"""Case document master repositories.

The seed repository keeps the current deterministic data while the public
case_docs module owns repository selection.
"""

from collections.abc import Iterable
from typing import Protocol

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

    resolved_placeholders: list[CaseDocResolvedPlaceholderData] = []
    for assignment in host_assignments:
        if assignment.device_type != "SBC":
            continue

        device_values = _DEVICE_VALUES_BY_HOST_NAME.get(assignment.host_name)
        if device_values is None:
            continue

        resolved_placeholders.append(
            CaseDocResolvedPlaceholderData(
                placeholder="SBC_COMMAND_FLOATING_IP",
                value=device_values["command_floating_ip"],
                source_table="SBC",
                source_column="command_floating_ip",
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
