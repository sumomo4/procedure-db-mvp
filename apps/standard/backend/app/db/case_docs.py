"""Case document master and context resolution helpers."""

from app.core.config import AppSettings
from app.core.responses import (
    CaseDocMasterOptionsData,
    CaseDocPlaceholderMappingEnabledRequest,
    CaseDocPlaceholderMappingItemData,
    CaseDocPlaceholderMappingListData,
    CaseDocPlaceholderMappingUpsertRequest,
    CaseDocResolveContextData,
    CaseDocResolveContextRequest,
    CaseDocUnitConfigListData,
)
from app.db.case_doc_repositories import (
    CaseDocMasterRepository,
    ExportFileCaseDocMasterRepository,
    SeedCaseDocMasterRepository,
)


_SUPPORTED_MASTER_SOURCES = {"seed", "export_file"}


def get_case_doc_master_repository(settings: AppSettings) -> CaseDocMasterRepository:
    """Select the case document master repository from runtime settings."""

    if settings.case_doc_master_source not in _SUPPORTED_MASTER_SOURCES:
        raise ValueError(f"unsupported case document master source: {settings.case_doc_master_source}")
    if settings.case_doc_master_source == "export_file":
        return ExportFileCaseDocMasterRepository(
            settings.case_doc_access_export_dir,
            settings.case_doc_placeholder_mapping_path,
        )
    return SeedCaseDocMasterRepository(settings.case_doc_placeholder_mapping_path)


def list_case_doc_prefectures(settings: AppSettings) -> CaseDocMasterOptionsData:
    """Return prefectures available for case document generation."""

    return get_case_doc_master_repository(settings).list_prefectures()


def list_case_doc_buildings(settings: AppSettings, prefecture: str) -> CaseDocMasterOptionsData:
    """Return buildings filtered by prefecture."""

    return get_case_doc_master_repository(settings).list_buildings(prefecture)


def list_case_doc_unit_configs(
    settings: AppSettings,
    prefecture: str,
    building: str,
) -> CaseDocUnitConfigListData:
    """Return unit configuration candidates for selected location."""

    return get_case_doc_master_repository(settings).list_unit_configs(prefecture, building)


def resolve_case_doc_context(
    settings: AppSettings,
    payload: CaseDocResolveContextRequest,
) -> CaseDocResolveContextData:
    """Resolve generation context without accepting manual placeholder values."""

    return get_case_doc_master_repository(settings).resolve_context(payload)


def list_case_doc_placeholder_mappings(settings: AppSettings) -> CaseDocPlaceholderMappingListData:
    """Return placeholder mappings used for case document generation."""

    return get_case_doc_master_repository(settings).list_placeholder_mappings()


def validate_case_doc_placeholder_mapping(
    settings: AppSettings,
    payload: CaseDocPlaceholderMappingUpsertRequest,
) -> CaseDocPlaceholderMappingItemData:
    """Validate a placeholder mapping without writing it."""

    return get_case_doc_master_repository(settings).validate_placeholder_mapping(payload)


def create_case_doc_placeholder_mapping(
    settings: AppSettings,
    payload: CaseDocPlaceholderMappingUpsertRequest,
) -> CaseDocPlaceholderMappingItemData:
    """Create a placeholder mapping."""

    return get_case_doc_master_repository(settings).create_placeholder_mapping(payload)


def update_case_doc_placeholder_mapping(
    settings: AppSettings,
    name: str,
    payload: CaseDocPlaceholderMappingUpsertRequest,
) -> CaseDocPlaceholderMappingItemData:
    """Update a placeholder mapping."""

    return get_case_doc_master_repository(settings).update_placeholder_mapping(name, payload)


def set_case_doc_placeholder_mapping_enabled(
    settings: AppSettings,
    name: str,
    payload: CaseDocPlaceholderMappingEnabledRequest,
) -> CaseDocPlaceholderMappingItemData:
    """Enable or disable a placeholder mapping."""

    return get_case_doc_master_repository(settings).set_placeholder_mapping_enabled(name, payload)
