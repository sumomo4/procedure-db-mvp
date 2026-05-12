"""Case document master and context resolution helpers."""

from app.core.config import AppSettings
from app.core.responses import (
    CaseDocMasterOptionsData,
    CaseDocResolveContextData,
    CaseDocResolveContextRequest,
    CaseDocUnitConfigListData,
)
from app.db.case_doc_repositories import CaseDocMasterRepository, SeedCaseDocMasterRepository


_SUPPORTED_MASTER_SOURCES = {"seed"}


def get_case_doc_master_repository(settings: AppSettings) -> CaseDocMasterRepository:
    """Select the case document master repository from runtime settings."""

    if settings.case_doc_master_source not in _SUPPORTED_MASTER_SOURCES:
        raise ValueError(f"unsupported case document master source: {settings.case_doc_master_source}")
    return SeedCaseDocMasterRepository()


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
