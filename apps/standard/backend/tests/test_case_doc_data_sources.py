"""Namespace isolation and backward-compatible snapshots for Access exports."""

from pathlib import Path

import pytest
import yaml

from app.core.responses import CaseDocDataSourceData, CaseDocDataSourceListData, CaseDocResolveContextRequest
from app.db import case_doc_data_sources as sources
from app.db.case_docs import resolve_case_doc_context
from app.db.case_doc_repositories import ExportFileCaseDocMasterRepository, _resolve_export_file_path
from app.db.case_doc_instances import _summary_from_row
from test_case_doc_placeholder_keys import _write_workbook


@pytest.fixture
def source_settings(tmp_path, test_settings):
    root = tmp_path / "exports"
    root.mkdir()
    mapping = tmp_path / "mapping.yml"
    mapping.write_text("version: 1\nplaceholders: []\n", encoding="utf-8")
    return test_settings.model_copy(update={"case_doc_master_source": "export_file", "case_doc_access_export_dir": str(root), "case_doc_placeholder_mapping_path": str(mapping)})


@pytest.mark.parametrize("source_id", ["../uni", "a/b", "a\\b", "a:b", "", ".", "UNI", "a" * 41])
def test_unsafe_namespace_is_rejected(source_settings, source_id):
    with pytest.raises(ValueError):
        sources._paths(source_settings, source_id)


def test_ssc_uses_its_own_directory_and_preserves_mapping(source_settings):
    directory, mapping = sources._paths(source_settings, "ssc")
    assert directory == Path(source_settings.case_doc_access_export_dir) / "ssc"
    assert mapping == Path(source_settings.case_doc_placeholder_mapping_path)
    scoped, source = sources.select_data_source(source_settings, None)
    assert scoped.case_doc_access_export_dir == str(directory)
    assert scoped.case_doc_placeholder_mapping_path == str(mapping)
    assert source is None
    assert source_settings.case_doc_access_export_dir == str(directory.parent)


def test_legacy_seed_settings_are_unchanged(test_settings):
    assert sources.select_data_source(test_settings, None) == (test_settings, None)


def test_same_file_and_placeholder_names_resolve_only_within_selected_db(source_settings, monkeypatch):
    for source_id, address in [("ssc", "192.0.2.10"), ("uni", "198.51.100.20"), ("third", "203.0.113.30")]:
        directory, mapping = sources._paths(source_settings, source_id)
        directory.mkdir(parents=True, exist_ok=True)
        mapping.parent.mkdir(parents=True, exist_ok=True)
        _write_workbook(directory / "unit_config.xlsx", [["unit_config_id", "fs_cluster_name", "block", "prefecture", "building", "GUI_0"], ["same-unit", "cluster", "B1", "Tokyo", "building", "same-host"]])
        _write_workbook(directory / "GUI.xlsx", [["host_name", "ip"], ["same-host", address]])
        mapping.write_text(yaml.safe_dump({"placeholders": [{"name": "GUI_IP", "enabled": True, "scope": "device", "device_type": "GUI", "source_file": "GUI.xlsx", "key_column": "host_name", "value_column": "ip", "source_column": "ip"}]}), encoding="utf-8")
    items = [sources._to_data(source_settings, {"source_id": key, "name": key.upper(), "enabled": True, "description": ""}) for key in ("ssc", "uni", "third")]
    monkeypatch.setattr(sources, "list_data_sources", lambda *_args, **_kwargs: CaseDocDataSourceListData(items=items))
    for item, expected in zip(items, ["192.0.2.10", "198.51.100.20", "203.0.113.30"], strict=True):
        result = resolve_case_doc_context(source_settings, CaseDocResolveContextRequest(data_source_id=item.source_id, source_doc_id=1, prefecture="Tokyo", building="building", unit_config_id="same-unit", target_slot_groups=[["GUI_0"]]))
        assert next(value.value for value in result.resolved_placeholders if value.placeholder == "GUI_IP") == expected
        assert result.data_source_id == item.source_id and result.data_source_name == item.name
        assert len(result.data_source_revision) == 64
    legacy = resolve_case_doc_context(source_settings, CaseDocResolveContextRequest(
        source_doc_id=1, prefecture="Tokyo", building="building", unit_config_id="same-unit", target_slot_groups=[["GUI_0"]],
    ))
    assert next(value.value for value in legacy.resolved_placeholders if value.placeholder == "GUI_IP") == "192.0.2.10"
    old_identifier = resolve_case_doc_context(source_settings, CaseDocResolveContextRequest(
        data_source_id="sbc", source_doc_id=1, prefecture="Tokyo", building="building", unit_config_id="same-unit", target_slot_groups=[["GUI_0"]],
    ))
    assert old_identifier.data_source_id == "ssc" and old_identifier.data_source_name == "SSC"
    assert next(value.value for value in old_identifier.resolved_placeholders if value.placeholder == "GUI_IP") == "192.0.2.10"


def test_legacy_master_api_reads_only_sbc_subdirectory(client, test_settings, tmp_path):
    test_settings.case_doc_master_source = "export_file"
    test_settings.case_doc_access_export_dir = str(tmp_path)
    (tmp_path / "ssc").mkdir()
    rows = [["unit_config_id", "fs_cluster_name", "block", "prefecture", "building", "GUI_0"]]
    _write_workbook(tmp_path / "unit_config.xlsx", [*rows, ["root", "ROOT", "B1", "Root", "building", "root-host"]])
    _write_workbook(tmp_path / "ssc" / "unit_config.xlsx", [*rows, ["sbc", "SBC", "B1", "Sbc", "building", "sbc-host"]])
    response = client.get("/api/v1/case-docs/master/prefectures")
    assert response.status_code == 200
    assert [item["value"] for item in response.json()["data"]["items"]] == ["Sbc"]


def test_missing_sbc_directory_never_reads_legacy_root(client, test_settings, tmp_path):
    test_settings.case_doc_master_source = "export_file"
    test_settings.case_doc_access_export_dir = str(tmp_path)
    _write_workbook(tmp_path / "unit_config.xlsx", [["prefecture", "building", "GUI_0"], ["Root", "building", "root-host"]])
    (tmp_path / "sbc").mkdir()
    _write_workbook(tmp_path / "sbc" / "unit_config.xlsx", [["prefecture", "building", "GUI_0"], ["Old", "building", "old-host"]])
    assert client.get("/api/v1/case-docs/master/prefectures").status_code == 400


def test_sbc_directory_link_cannot_escape_source_root(source_settings, tmp_path):
    external = tmp_path / "other-db"
    external.mkdir()
    link = Path(source_settings.case_doc_access_export_dir) / "ssc"
    try:
        link.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("Symbolic links unavailable")
    with pytest.raises(ValueError):
        sources._paths(source_settings, "ssc")


def test_old_sbc_identifier_cannot_be_registered_as_a_second_source(client, source_settings):
    with pytest.raises(ValueError, match="旧識別子"):
        sources._paths(source_settings, "sbc")
    response = client.post("/api/v1/case-docs/data-sources", json={"source_id": "sbc", "name": "Other DB"})
    assert response.status_code == 400
    assert "旧識別子" in response.json()["message"]


@pytest.mark.parametrize("source_id,enabled", [("missing", True), ("uni", False)])
def test_unknown_or_disabled_source_never_falls_back(source_settings, monkeypatch, source_id, enabled):
    monkeypatch.setattr(sources, "list_data_sources", lambda *_a, **_k: CaseDocDataSourceListData(items=[CaseDocDataSourceData(source_id="uni", name="UNI", enabled=enabled)]))
    with pytest.raises(ValueError):
        sources.select_data_source(source_settings, source_id)


def test_missing_mapping_is_not_initialized_from_sbc(source_settings, monkeypatch):
    monkeypatch.setattr(sources, "list_data_sources", lambda *_a, **_k: CaseDocDataSourceListData(items=[CaseDocDataSourceData(source_id="uni", name="UNI")]))
    with pytest.raises(ValueError):
        sources.select_data_source(source_settings, "uni")
    assert not sources._paths(source_settings, "uni")[1].exists()


def test_revision_ignores_other_db_directories(source_settings):
    before = sources.data_source_revision(source_settings)
    other = Path(source_settings.case_doc_access_export_dir) / "uni"
    other.mkdir()
    (other / "GUI.xlsx").write_bytes(b"other-db")
    assert sources.data_source_revision(source_settings) == before
    Path(source_settings.case_doc_placeholder_mapping_path).write_text("version: 2\nplaceholders: []\n", encoding="utf-8")
    assert sources.data_source_revision(source_settings) != before


def test_file_link_cannot_read_another_db(source_settings, tmp_path):
    external = tmp_path / "external.xlsx"
    external.write_bytes(b"not readable through selected source")
    link = Path(source_settings.case_doc_access_export_dir) / "GUI.xlsx"
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip("Symbolic links unavailable")
    with pytest.raises(ValueError):
        _resolve_export_file_path(link.parent, [link.name])
    repository = ExportFileCaseDocMasterRepository(str(link.parent), source_settings.case_doc_placeholder_mapping_path)
    assert repository.list_placeholder_source_files().items == []


def test_admin_registration_is_not_available_to_other_roles(non_admin_client):
    payload = {"source_id": "uni", "name": "UNI"}
    assert non_admin_client.post("/api/v1/case-docs/data-sources", json=payload).status_code == 403
    assert non_admin_client.put("/api/v1/case-docs/data-sources/uni", json=payload).status_code == 403
    assert non_admin_client.get("/api/v1/case-docs/data-sources?include_disabled=true").status_code == 403


def test_source_list_is_available_without_admin_role(non_admin_client, monkeypatch):
    monkeypatch.setattr("app.routers.case_docs.list_data_sources", lambda *_: CaseDocDataSourceListData(items=[CaseDocDataSourceData(source_id="ssc", name="SSC")]))
    assert non_admin_client.get("/api/v1/case-docs/data-sources").json()["data"]["items"][0]["source_id"] == "ssc"


@pytest.mark.parametrize("endpoint,helper", [
    ("blocks", "list_case_doc_blocks"),
    ("prefectures", "list_case_doc_prefectures"),
    ("buildings?prefecture=Tokyo", "list_case_doc_buildings"),
    ("buildings?block=West", "list_case_doc_buildings"),
    ("unit-config?prefecture=Tokyo&building=building", "list_case_doc_unit_configs"),
    ("unit-config?block=West&building=building", "list_case_doc_unit_configs"),
])
def test_missing_unit_configuration_returns_actionable_error(non_admin_client, monkeypatch, endpoint, helper):
    def unavailable(*_args, **_kwargs):
        raise ValueError("missing unit_config.xlsx")

    monkeypatch.setattr("app.routers.case_docs." + helper, unavailable)
    response = non_admin_client.get("/api/v1/case-docs/master/" + endpoint)
    assert response.status_code == 400
    assert "ユニット構成" in response.json()["message"]


def test_saved_and_legacy_case_metadata_does_not_depend_on_live_catalog():
    row = {"case_document_id": 1, "case_document_key": "CASE-1", "case_name": "Test", "source_doc_id": 1,
           "source_doc_key": "BP-1", "source_doc_name": "Source", "unit_config_id": "same-unit", "status": "active",
           "total_count": 1, "checked_count": 0, "skipped_count": 0, "pending_count": 1,
           "created_by": "Tester", "created_at": "2026-10-22", "updated_at": "2026-10-22"}
    legacy = _summary_from_row(row)
    assert (legacy.data_source_id, legacy.data_source_name, legacy.data_source_revision) == ("ssc", "SSC", None)
    old_default = _summary_from_row({**row, "context_json": {"data_source_id": "sbc", "data_source_name": "SBC", "data_source_revision": "old-revision"}})
    assert (old_default.data_source_id, old_default.data_source_name, old_default.data_source_revision) == ("ssc", "SSC", "old-revision")
    old_custom = _summary_from_row({**row, "context_json": {"data_source_id": "sbc", "data_source_name": "Custom name"}})
    assert (old_custom.data_source_id, old_custom.data_source_name) == ("ssc", "Custom name")
    new_custom = _summary_from_row({**row, "context_json": {"data_source_id": "ssc", "data_source_name": "SBC"}})
    assert (new_custom.data_source_id, new_custom.data_source_name) == ("ssc", "SBC")
    saved = _summary_from_row({**row, "context_json": {"data_source_id": "uni", "data_source_name": "UNI at creation", "data_source_revision": "old-revision"}})
    assert (saved.data_source_id, saved.data_source_name, saved.data_source_revision) == ("uni", "UNI at creation", "old-revision")
