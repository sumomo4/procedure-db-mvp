"""UNI target locations and hostname lookups without a unit-configuration file."""

from functools import cached_property
from pathlib import Path

from app.core.responses import (
    CaseDocHostAssignmentData, CaseDocMasterOptionsData, CaseDocResolveContextData,
    CaseDocResolveContextRequest, CaseDocResolvedPlaceholderData, CaseDocUniCandidatesData,
    CaseDocUniCandidateDeviceData, CaseDocUniTargetContextData, CaseDocUniWorkContextData,
    CaseDocUniWorkSelection, CaseDocUnitConfigListData,
)
from app.db.case_doc_repositories import (
    ExportFileCaseDocMasterRepository, _as_option, _normalize_key, _read_placeholder_source_table,
    _resolve_common_placeholders, _to_target_device_slots,
)
from app.db.case_doc_workflows import generate_uni_hosts, load_uni_master

UNI_KINDS = {"USBE", "USBH", "USBM", "USCE", "USLE"}


def _prefecture_key(value):
    return value[:-1] if value.endswith(("府", "県")) or value == "東京都" else value


class UniCaseDocMasterRepository(ExportFileCaseDocMasterRepository):
    def __init__(self, export_dir: str, mapping_path: str, profile_path: str):
        super().__init__(export_dir, mapping_path)
        self.profile_path = Path(profile_path)
        self._tables = {}

    @cached_property
    def master(self):
        return load_uni_master(self.profile_path)

    def _load_unit_configs(self):
        return []

    def list_blocks(self):
        return CaseDocMasterOptionsData(items=[_as_option(value) for value in sorted({item.block for item in self.master.buildings})])

    def list_prefectures(self):
        return CaseDocMasterOptionsData(items=[_as_option(value) for value in sorted({item.prefecture for item in self.master.buildings})])

    def list_buildings(self, prefecture=None, *, block=None):
        return CaseDocMasterOptionsData(items=[_as_option(value) for value in sorted({item.building for item in self.master.buildings
            if (prefecture is None or item.prefecture == prefecture) and (block is None or item.block == block)})])

    def list_unit_configs(self, prefecture, building, *, block=None):
        return CaseDocUnitConfigListData(items=[])

    def list_clusters(self, block, building):
        self._building(block, building)
        return CaseDocMasterOptionsData(items=[_as_option(str(number)).model_copy(update={"label": f"{number} / {area}"})
            for number, area in sorted(self.master.areas.get(block, {}).items())])

    def _building(self, block, building):
        match = next((item for item in self.master.buildings if item.block == block and item.building == building), None)
        if match is None:
            raise ValueError("UNIの命名規則に選択したブロック・ビルがありません。")
        return match

    def _table(self, name):
        if not name or Path(name).name != name or any(char in name for char in "/\\:"):
            raise ValueError("UNIの参照ファイル名が不正です。")
        path = self.export_dir / name
        if path.resolve().parent != self.export_dir.resolve():
            raise ValueError("UNIの参照ファイルは選択したDB内に配置してください。")
        if not path.is_file():
            raise ValueError(f"UNIの参照ファイル「{name}」がありません。")
        if name not in self._tables:
            self._tables[name] = _read_placeholder_source_table(path)
        return self._tables[name]

    def _record(self, file, key, host):
        table = self._table(file)
        normalized_key = _normalize_key(key)
        if normalized_key not in {_normalize_key(column) for column in table.columns}:
            raise ValueError(f"{file}にキー列「{key}」がありません。")
        rows = [row for row in table.rows if row.lookup.get(normalized_key) == host]
        if len(rows) > 1:
            raise ValueError(f"{file}のキー列「{key}」にホスト名「{host}」が重複しています。")
        return rows[0].lookup if rows else None

    def target_candidates(self, selection: CaseDocUniWorkSelection) -> CaseDocUniCandidatesData:
        building = self._building(selection.block, selection.building)
        area = self.master.areas.get(selection.block, {}).get(selection.cluster_no)
        if area is None:
            raise ValueError("選択したブロックのクラスタ番号は、命名規則の収容エリア表で未設定です。")
        work = CaseDocUniWorkContextData(**selection.model_dump(), prefecture=building.prefecture, area=area,
            hostname_prefix=building.prefix, pair_building=building.pair_building)
        devices, tts_hosts = [], set()
        for assignment in generate_uni_hosts(building, selection.cluster_no):
            key = assignment.column_name.replace("系", "")
            available, message = True, ""
            try:
                definition = self._record("TTS_定義.xlsx", "ホスト名", assignment.host_name)
                device = self._record("装置追加.xlsx", "ホスト名", assignment.host_name)
                if definition is None or device is None:
                    available, message = False, "抽出ファイルに一致するホスト名がありません。"
                elif definition.get(_normalize_key("設置ビル")) != building.building:
                    available, message = False, "TTS_定義の設置ビルと選択したビルが一致しません。"
                elif _prefecture_key(definition.get(_normalize_key("設置府県"), "")) != _prefecture_key(building.prefecture):
                    available, message = False, "TTS_定義の設置府県と命名規則が一致しません。"
                if available:
                    for column in ("TTSホスト名①", "TTSホスト名②"):
                        if host := definition.get(_normalize_key(column)):
                            tts_hosts.add(host)
            except OSError:
                available, message = False, "UNIの抽出ファイルを読み込めませんでした。"
            except ValueError as error:
                available, message = False, str(error)
            devices.append(CaseDocUniCandidateDeviceData(**{**assignment.model_dump(), "slot_key": key}, available=available, message=message))
        for index, host in enumerate(sorted(tts_hosts)):
            try:
                available = self._record("TTS.xlsx", "TTSホスト名", host) is not None
                message = "" if available else "TTS.xlsxに一致するホスト名がありません。"
            except OSError:
                available, message = False, "TTSの抽出ファイルを読み込めませんでした。"
            except ValueError as error:
                available, message = False, str(error)
            devices.append(CaseDocUniCandidateDeviceData(slot_key=f"TTS_{index}", device_type="TTS", system=None,
                host_name=host, column_name=f"TTS {index + 1}", available=available, message=message))
        return CaseDocUniCandidatesData(work=work, devices=devices)

    def resolve_context(self, payload: CaseDocResolveContextRequest) -> CaseDocResolveContextData:
        if not payload.uni_targets:
            raise ValueError("UNIではtargetごとのブロック・ビル・クラスタ番号・対象装置を指定してください。")
        if payload.target_slot_key or payload.target_slot_keys or payload.target_slot_groups:
            raise ValueError("UNIの対象装置にはUNI専用の選択項目を使用してください。")
        mappings = self._load_placeholder_mappings()
        if any(mapping.enabled and mapping.scope == "unit" for mapping in mappings):
            raise ValueError("UNIでは「ユニット構成の値」は使用できません。プレースホルダ設定を確認してください。")
        groups, hosts, works, resolved = [], [], [], []
        for number, selection in enumerate(payload.uni_targets, 1):
            candidates = self.target_candidates(selection)
            if len(set(selection.device_keys)) != len(selection.device_keys):
                raise ValueError("同じtarget内の対象装置が重複しています。")
            available = {item.slot_key: item for item in candidates.devices if item.available}
            if any(key not in available for key in selection.device_keys):
                raise ValueError(f"target {number}の対象装置が未登録または照合できません。候補を再確認してください。")
            local = {key: CaseDocHostAssignmentData(**{**item.model_dump(exclude={"available", "message"}),
                "slot_key": item.device_type + f"_T{number}" + (f"_{key.split('_', 1)[1]}" if "_" in key else "")})
                for key, item in available.items()}
            group = [local[key] for key in selection.device_keys]
            groups.append(group)
            hosts.extend(local.values())
            works.append(CaseDocUniTargetContextData(**candidates.work.model_dump(), target_no=number,
                slot_keys=[item.slot_key for item in local.values()]))
            for target in group:
                for mapping in mappings:
                    if not mapping.enabled or mapping.scope != "device" or mapping.device_type not in {target.device_type, "UNI" if target.device_type in UNI_KINDS else "TTS"}:
                        continue
                    source = target
                    if mapping.source_device_type and mapping.source_device_type not in {target.device_type, "UNI" if target.device_type in UNI_KINDS else "TTS"}:
                        references = [item for item in local.values() if item.device_type == mapping.source_device_type
                            and item.system == target.system]
                        if len(references) != 1:
                            continue
                        source = references[0]
                    row = self._record(mapping.source_file, mapping.key_column, source.host_name)
                    value = row.get(_normalize_key(mapping.value_column)) if row else None
                    if value:
                        resolved.append(CaseDocResolvedPlaceholderData(placeholder=mapping.name, value=value,
                            source_table=Path(mapping.source_file).stem, source_column=mapping.source_column, host_name=target.host_name))
        common = self._load_common_values(mappings)
        return CaseDocResolveContextData(source_doc_id=payload.source_doc_id, generation_mode="uni", unit_config=None,
            target_contexts=works, target_assignment=groups[0][0], target_assignments=[group[0] for group in groups],
            target_groups=groups, target_device_slots=_to_target_device_slots([group[0] for group in groups], groups),
            host_assignments=hosts, common_values=common, resolved_placeholders=[*resolved, *_resolve_common_placeholders(common)])
