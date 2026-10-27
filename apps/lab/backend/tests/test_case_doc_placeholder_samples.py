"""Unsaved samples match generation and never initialize or change configuration."""

from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from app.core.case_doc_generation import _build_placeholder_values_for_assignment
from app.core.responses import CaseDocPlaceholderSampleRequest, CaseDocResolveContextRequest
from app.db.case_doc_placeholder_samples import list_placeholder_sample_options, preview_placeholder_sample
from app.db.case_doc_repositories import ExportFileCaseDocMasterRepository
from test_case_doc_placeholder_keys import _mapping, _write_workbook, GUI_0_COLUMN, GUI_1_COLUMN, HOST_COLUMN, UNIT_FILE


@pytest.fixture
def sample_settings(tmp_path, test_settings):
    _write_workbook(tmp_path / UNIT_FILE, [
        ["fs_cluster_name", "block", "prefecture", "building", GUI_0_COLUMN, GUI_1_COLUMN, "HFS_1", "note"],
        ["cluster-1", "B1", "Tokyo", "test-building", "GUI-A", "GUI-B", "HFS-B", "shared-unit-value"],
        ["cluster-2", "B2", "Osaka", "second-building", "GUI-C", "GUI-D", "", "other-value"],
    ])
    _write_workbook(tmp_path / "GUI.xlsx", [
        [HOST_COLUMN, "address"], ["GUI-A", "10.0.0.1"], ["GUI-B", "10.0.0.2"],
    ])
    return test_settings.model_copy(update={
        "case_doc_master_source": "export_file", "case_doc_access_export_dir": str(tmp_path),
        "case_doc_placeholder_mapping_path": str(tmp_path / "placeholder_mapping.yml"),
    })


def request(mapping=None, **changes):
    return CaseDocPlaceholderSampleRequest.model_validate({
        "mapping": mapping or _mapping("GUI_ADDRESS", HOST_COLUMN, "address", source_file="GUI.xlsx"),
        "prefecture": "Tokyo", "building": "test-building", "unit_config_id": "unit-export-1",
        "target_slot_key": "GUI_0", **changes,
    })


def fingerprint(directory):
    return {str(path.relative_to(directory)): sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob("*") if path.is_file()}


def test_options_and_unsaved_sample_never_create_mapping_file(sample_settings, tmp_path):
    before = fingerprint(tmp_path)
    units = list_placeholder_sample_options(sample_settings).items
    assert len(units) == 2
    unit = next(item for item in units if item.unit_config.prefecture == "Tokyo")
    assert {item.slot_key for item in unit.devices} >= {"GUI_0", "GUI_1", "HFS_1"}
    result = preview_placeholder_sample(sample_settings, request())
    assert (result.status, result.before, result.after) == ("resolved", "{{GUI_ADDRESS}}", "10.0.0.1")
    assert (result.source_file, result.row_number, result.key_column, result.value_column) == ("GUI.xlsx", 2, HOST_COLUMN, "address")
    assert result.lookup_value == "GUI-A"
    assert fingerprint(tmp_path) == before
    assert not Path(sample_settings.case_doc_placeholder_mapping_path).exists()


def test_unsaved_draft_does_not_read_or_replace_persisted_mapping(sample_settings, tmp_path):
    path = Path(sample_settings.case_doc_placeholder_mapping_path)
    path.write_text("deliberately: [invalid persisted mapping", encoding="utf-8")
    before = fingerprint(tmp_path)
    assert preview_placeholder_sample(sample_settings, request()).after == "10.0.0.1"
    assert fingerprint(tmp_path) == before


@pytest.mark.parametrize("slot,column,expected", [("GUI_0", GUI_0_COLUMN, "GUI-A"), ("GUI_1", GUI_1_COLUMN, "GUI-B")])
def test_definition_specific_unit_key_matches_generation(sample_settings, slot, column, expected):
    mapping = _mapping("UNIT_GUI_HOSTNAME", column, column)
    payload = request(mapping, target_slot_key=slot)
    result = preview_placeholder_sample(sample_settings, payload)
    path = Path(sample_settings.case_doc_placeholder_mapping_path)
    path.write_text(yaml.safe_dump({"placeholders": [mapping]}), encoding="utf-8")
    repository = ExportFileCaseDocMasterRepository(sample_settings.case_doc_access_export_dir, str(path))
    context = repository.resolve_context(CaseDocResolveContextRequest(
        source_doc_id=1, prefecture=payload.prefecture, building=payload.building,
        unit_config_id=payload.unit_config_id, target_slot_key=slot,
    ))
    assert result.status == "resolved"
    assert result.after == expected == _build_placeholder_values_for_assignment(context, context.target_assignment)[mapping["name"]]


def test_unit_scope_works_without_target_and_reports_physical_row(sample_settings):
    mapping = _mapping("UNIT_NOTE", "", "note", scope="unit", device_type=None)
    result = preview_placeholder_sample(sample_settings, request(mapping, target_slot_key=None))
    assert (result.status, result.after, result.row_number) == ("resolved", "shared-unit-value", 2)


def test_cross_device_reference_uses_matching_slot(sample_settings):
    mapping = _mapping("HFS_GUI_ADDRESS", HOST_COLUMN, "address", source_file="GUI.xlsx", device_type="HFS", source_device_type="GUI")
    result = preview_placeholder_sample(sample_settings, request(mapping, target_slot_key="HFS_1"))
    assert (result.status, result.after, result.lookup_value, result.row_number) == ("resolved", "10.0.0.2", "GUI-B", 3)


@pytest.mark.parametrize("changes,status", [
    ({"enabled": False}, "disabled"), ({"device_type": "RAID"}, "not_applicable"),
    ({"source_device_type": "RAID"}, "reference_missing"),
    ({"key_column": "unknown-key"}, "missing_column"), ({"value_column": "unknown-value"}, "missing_column"),
    ({"source_file": "missing.xlsx"}, "source_error"),
])
def test_specific_failure_states(sample_settings, changes, status):
    mapping = _mapping("GUI_ADDRESS", HOST_COLUMN, "address", source_file="GUI.xlsx", **{})
    mapping.update(changes)
    result = preview_placeholder_sample(sample_settings, request(mapping))
    assert result.status == status
    assert result.after == result.before


@pytest.mark.parametrize("rows,status", [
    ([[HOST_COLUMN, "address"], ["unrelated", "10.0.0.1"]], "lookup_mismatch"),
    ([[HOST_COLUMN, "address"], ["GUI-A", ""]], "empty_value"),
    ([[HOST_COLUMN, "host_name", "address"], ["", "GUI-A", "wrong"]], "lookup_mismatch"),
])
def test_empty_values_and_explicit_blank_key(sample_settings, tmp_path, rows, status):
    _write_workbook(tmp_path / "GUI.xlsx", rows)
    result = preview_placeholder_sample(sample_settings, request())
    assert result.status == status


def test_alias_and_last_nonempty_matching_row(sample_settings, tmp_path):
    _write_workbook(tmp_path / "GUI.xlsx", [["host_name", "address"], ["GUI-A", "first"], [], ["GUI-A", "last"], ["GUI-A", ""]])
    result = preview_placeholder_sample(sample_settings, request())
    assert (result.status, result.after, result.row_number, result.key_column) == ("resolved", "last", 4, "host_name")


def test_value_alias_trace_shows_actual_nonempty_column(sample_settings, tmp_path):
    _write_workbook(tmp_path / "GUI.xlsx", [[HOST_COLUMN, "address", "fallback"], ["GUI-A", "", "alias-value"]])
    mapping = _mapping("GUI_ADDRESS", HOST_COLUMN, "address", source_file="GUI.xlsx", source_column="fallback")
    result = preview_placeholder_sample(sample_settings, request(mapping))
    assert (result.status, result.after, result.value_column) == ("resolved", "alias-value", "fallback")


def common_mapping(**changes):
    return _mapping("COMMON_TEST", "key", "value", scope="common", source_file="case_common_values.xlsx", device_type=None, key_value="COMMON_TEST", **changes)


def test_common_scope_matches_generation(sample_settings, tmp_path):
    _write_workbook(tmp_path / "case_common_values.xlsx", [["key", "value"], ["COMMON_TEST", "shared-value"]])
    result = preview_placeholder_sample(sample_settings, request(common_mapping(), target_slot_key=None))
    assert (result.status, result.after, result.row_number) == ("resolved", "shared-value", 2)


def test_common_name_mismatch_does_not_claim_replacement(sample_settings, tmp_path):
    _write_workbook(tmp_path / "case_common_values.xlsx", [["key", "value"], ["OTHER_KEY", "shared-value"]])
    mapping = common_mapping()
    mapping["key_value"] = "OTHER_KEY"
    result = preview_placeholder_sample(sample_settings, request(mapping))
    assert result.status == "unresolved"
    assert result.after == result.before


def test_common_first_match_empty_is_not_replaced_by_later_row(sample_settings, tmp_path):
    _write_workbook(tmp_path / "case_common_values.xlsx", [["key", "value"], ["COMMON_TEST", ""], ["COMMON_TEST", "later"]])
    result = preview_placeholder_sample(sample_settings, request(common_mapping()))
    assert (result.status, result.row_number) == ("empty_value", 2)


@pytest.mark.parametrize("name", ["../GUI.xlsx", "folder/GUI.xlsx", "folder\\GUI.xlsx", "C:GUI.xlsx"])
def test_sample_rejects_path_traversal(sample_settings, name):
    mapping = _mapping("GUI_ADDRESS", HOST_COLUMN, "address", source_file=name)
    with pytest.raises(ValueError, match="filename"):
        preview_placeholder_sample(sample_settings, request(mapping))


@pytest.mark.parametrize("changes", [
    {"unit_config_id": "not-a-unit"}, {"target_slot_key": "GUI_99"},
    {"target_slot_key": None}, {"prefecture": "not-a-prefecture"},
])
def test_sample_requires_valid_explicit_selection(sample_settings, changes):
    with pytest.raises(ValueError):
        preview_placeholder_sample(sample_settings, request(**changes))


def test_routes_are_read_only_and_accept_unsaved_definition(client, test_settings, sample_settings, tmp_path):
    directory = tmp_path / "ssc"
    directory.mkdir()
    for name in (UNIT_FILE, "GUI.xlsx"):
        (directory / name).write_bytes((tmp_path / name).read_bytes())
    test_settings.case_doc_master_source = sample_settings.case_doc_master_source
    test_settings.case_doc_access_export_dir = sample_settings.case_doc_access_export_dir
    test_settings.case_doc_placeholder_mapping_path = sample_settings.case_doc_placeholder_mapping_path
    before = fingerprint(tmp_path)
    options = client.get("/api/v1/case-docs/placeholders/sample-options")
    assert options.status_code == 200
    assert len(options.json()["data"]["items"]) == 2
    response = client.post("/api/v1/case-docs/placeholders/sample", json=request().model_dump())
    assert response.status_code == 200
    assert response.json()["data"]["after"] == "10.0.0.1"
    assert fingerprint(tmp_path) == before


def test_sample_endpoints_require_admin(non_admin_client):
    assert non_admin_client.get("/api/v1/case-docs/placeholders/sample-options").status_code == 403
    assert non_admin_client.post("/api/v1/case-docs/placeholders/sample", json=request().model_dump()).status_code == 403


def test_seed_does_not_silently_preview_other_data(client):
    response = client.get("/api/v1/case-docs/placeholders/sample-options")
    assert response.status_code == 400
