"""Case document master and context resolution helpers."""

from app.core.config import AppSettings
from app.db.case_doc_data_sources import select_data_source, data_source_revision
from app.core.responses import (
    CaseDocMasterOptionsData,
    CaseDocPlaceholderMappingEnabledRequest,
    CaseDocPlaceholderMappingItemData,
    CaseDocPlaceholderMappingListData,
    CaseDocPlaceholderMappingUpsertRequest,
    CaseDocPlaceholderSourceFileListData,
    CaseDocPlaceholderSourcePreviewData,
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
        if settings.case_doc_generation_mode == "uni":
            from app.db.case_doc_uni import UniCaseDocMasterRepository

            return UniCaseDocMasterRepository(settings.case_doc_access_export_dir,
                settings.case_doc_placeholder_mapping_path, settings.case_doc_workflow_path)
        return ExportFileCaseDocMasterRepository(
            settings.case_doc_access_export_dir,
            settings.case_doc_placeholder_mapping_path,
        )
    return SeedCaseDocMasterRepository(settings.case_doc_placeholder_mapping_path)


def list_case_doc_prefectures(settings: AppSettings) -> CaseDocMasterOptionsData:
    """Return prefectures available for case document generation."""

    return get_case_doc_master_repository(settings).list_prefectures()


def list_case_doc_blocks(settings: AppSettings) -> CaseDocMasterOptionsData:
    """Return blocks available for case document generation."""

    return get_case_doc_master_repository(settings).list_blocks()


def list_case_doc_buildings(
    settings: AppSettings, prefecture: str | None = None, *, block: str | None = None,
) -> CaseDocMasterOptionsData:
    """Return buildings filtered by block and/or prefecture."""

    return get_case_doc_master_repository(settings).list_buildings(prefecture, block=block)


def list_case_doc_unit_configs(
    settings: AppSettings,
    prefecture: str | None,
    building: str,
    *,
    block: str | None = None,
) -> CaseDocUnitConfigListData:
    """Return unit configuration candidates for selected location."""

    return get_case_doc_master_repository(settings).list_unit_configs(prefecture, building, block=block)


def resolve_case_doc_context(
    settings: AppSettings,
    payload: CaseDocResolveContextRequest,
) -> CaseDocResolveContextData:
    """Resolve generation context without accepting manual placeholder values."""

    scoped_settings, source = select_data_source(settings, payload.data_source_id)
    if source is not None and not source.generation_ready:
        raise ValueError(source.generation_message or "選択した参照元DBの案件化に必要なファイルが不足しています。")
    if scoped_settings.case_doc_generation_mode != "uni" and payload.uni_targets is not None:
        raise ValueError("UNI専用の選択項目は、UNI方式の参照元DBで使用してください。")
    revision = data_source_revision(scoped_settings) if source is not None else None
    if payload.expected_data_source_revision and payload.expected_data_source_revision != revision:
        raise ValueError("参照データまたは命名規則が更新されています。置換結果を再確認してください。")
    context = get_case_doc_master_repository(scoped_settings).resolve_context(payload)
    if revision is not None and scoped_settings.case_doc_generation_mode == "uni" and data_source_revision(scoped_settings) != revision:
        raise ValueError("処理中に参照データが更新されました。もう一度確認してください。")
    if source is not None:
        context = context.model_copy(update={
            "data_source_id": source.source_id, "data_source_name": source.name,
            "data_source_revision": revision,
        })
    return context


def list_case_doc_placeholder_mappings(settings: AppSettings) -> CaseDocPlaceholderMappingListData:
    """Return placeholder mappings used for case document generation."""

    return get_case_doc_master_repository(settings).list_placeholder_mappings()


def list_case_doc_placeholder_source_files(settings: AppSettings) -> CaseDocPlaceholderSourceFileListData:
    """Return source files and columns available to placeholder mappings."""

    return get_case_doc_master_repository(settings).list_placeholder_source_files()


def get_case_doc_placeholder_source_preview(
    settings: AppSettings,
    source_file: str,
    fs_cluster_name: str | None,
    block: str | None,
    prefecture: str | None,
    page: int,
    page_size: int,
) -> CaseDocPlaceholderSourcePreviewData:
    """Return a filtered and paginated placeholder source table."""

    return get_case_doc_master_repository(settings).get_placeholder_source_preview(
        source_file,
        fs_cluster_name,
        block,
        prefecture,
        page,
        page_size,
    )


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
