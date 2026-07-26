"""Module resource routes for Sprint 2 implementation."""

import mimetypes
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import AppSettings
from app.core.excel_import import (
    build_module_create_request_from_sheet_data,
    build_module_create_request_from_workbook_bytes,
)
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApiResponse,
    ApprovalStatusDetailData,
    ApprovalStatusUpdateRequest,
    ExcelImportSheetRequest,
    ModuleCreateRequest,
    ModuleDetailData,
    ModuleDiffData,
    ModuleFolderDeleteRequest,
    ModuleFolderMoveRequest,
    ModuleFolderRenameRequest,
    ModuleListData,
    ModuleSimilarityCheckData,
    ModuleVersionListData,
    RouterEndpointData,
    RouterFoundationData,
    success_response,
)
from app.db.modules import (
    VALID_MODULE_STATUSES,
    create_module,
    delete_module_folder,
    get_module_detail,
    get_module_diff,
    get_module_diff_preview,
    get_module_row_image,
    get_module_version_status,
    list_module_versions,
    list_modules,
    move_modules_to_folder,
    rename_module_folder,
    update_module_version_status,
)
from app.routers.health import get_app_settings
from app.services.module_similarity import (
    check_similar_modules,
    validate_similarity_confirmation_token,
)


router = APIRouter(prefix="/modules", tags=["modules"])


def _resolve_module_image_file(settings: AppSettings, image_path: str) -> Path | None:
    """Resolve a stored image path without allowing access outside storage."""

    storage_root = Path(settings.module_image_storage_dir).resolve()
    candidate = Path(image_path)
    if not candidate.is_absolute():
        candidate = storage_root / candidate

    resolved_candidate = candidate.resolve(strict=False)
    if not resolved_candidate.is_relative_to(storage_root):
        return None

    if not resolved_candidate.is_file():
        return None

    return resolved_candidate


@router.get("", response_model=ApiResponse[ModuleListData])
def read_modules(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    keyword: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    folder_path: Annotated[str | None, Query(min_length=1)] = None,
    created_by: Annotated[str | None, Query(min_length=1)] = None,
    updated_from: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    updated_to: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    has_images: Annotated[str | None, Query(pattern=r"^(all|with|without)$")] = None,
    sort: Annotated[str | None, Query(pattern=r"^(key_asc|key_desc|updated_desc|updated_asc|status_asc)$")] = None,
) -> ApiResponse[ModuleListData]:
    """Return module list from PostgreSQL.

    Args:
        settings: Application settings provided by dependency injection.
        keyword: Optional search keyword.
        status_filter: Optional status filter.

    Returns:
        Common response containing module list data.

    Raises:
        HTTPException: If the status filter is invalid or the DB query fails.
    """

    normalized_status = status_filter.lower() if status_filter else None
    if normalized_status and normalized_status != "all" and normalized_status not in VALID_MODULE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be one of all, draft, review_requested, returned, published, archived.",
        )

    try:
        data = list_modules(
            settings,
            keyword=keyword,
            status_filter=normalized_status,
            folder_path=folder_path,
            created_by=created_by,
            updated_from=updated_from,
            updated_to=updated_to,
            has_images=has_images,
            sort=sort,
        )
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "モジュール一覧を取得しました。")


@router.patch("/folders", response_model=ApiResponse[ModuleListData])
def rename_module_folder_path(
    request: ModuleFolderRenameRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ModuleListData]:
    """Rename a virtual module folder path."""

    current_folder = request.current_folder_path.strip()
    new_folder = request.new_folder_path.strip()
    if not current_folder or not new_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="folder paths must not be empty.",
        )

    try:
        data = rename_module_folder(settings, current_folder, new_folder)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "フォルダ名を変更しました。")


@router.delete("/folders", response_model=ApiResponse[ModuleListData])
def delete_module_folder_path(
    request: ModuleFolderDeleteRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ModuleListData]:
    """Delete a virtual folder subtree and return its modules to uncategorized."""

    target_folder = request.folder_path.strip()
    if not target_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="folder_path must not be empty.",
        )
    if target_folder == "未分類":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uncategorized folder cannot be deleted.",
        )

    try:
        data = delete_module_folder(settings, target_folder)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "フォルダを削除し、格納されていたモジュールを未分類へ移動しました。")


@router.patch("/folders/modules", response_model=ApiResponse[ModuleListData])
def move_selected_modules_to_folder(
    request: ModuleFolderMoveRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ModuleListData]:
    """Move selected modules to a virtual folder path."""

    target_folder = request.folder_path.strip()
    if not request.module_ids or not target_folder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="module_ids and folder_path are required.",
        )

    try:
        data = move_modules_to_folder(settings, request.module_ids, target_folder)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "選択したモジュールをフォルダへ移動しました。")


@router.get("/foundation", response_model=ApiResponse[RouterFoundationData])
def read_module_router_foundation() -> ApiResponse[RouterFoundationData]:
    """Return the module API router foundation status.

    Returns:
        Common response containing planned module endpoints.
    """

    data = RouterFoundationData(
        resource="modules",
        sprint="Sprint 2",
        status="foundation-ready",
        planned_endpoints=[
            RouterEndpointData(method="GET", path="/api/v1/modules", purpose="モジュール一覧取得 / 検索"),
            RouterEndpointData(method="GET", path="/api/v1/modules/{module_id}", purpose="モジュール詳細取得"),
            RouterEndpointData(method="POST", path="/api/v1/modules", purpose="モジュール登録"),
            RouterEndpointData(method="PUT", path="/api/v1/modules/{module_id}", purpose="モジュール更新"),
        ],
    )
    return success_response(data, "モジュール API 構成情報を取得しました。")


@router.get("/{module_id}/diff", response_model=ApiResponse[ModuleDiffData])
def read_module_diff(
    module_id: int,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    from_version: Annotated[int, Query(ge=1)],
    to_version: Annotated[int, Query(ge=1)],
) -> ApiResponse[ModuleDiffData]:
    """Return a structured diff between two module versions."""

    try:
        data = get_module_diff(settings, module_id, from_version, to_version)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="比較対象のモジュール版が見つかりませんでした。",
        )

    return success_response(data, "モジュール差分を取得しました。")


@router.post("/{module_id}/diff-preview", response_model=ApiResponse[ModuleDiffData])
def read_module_diff_preview(
    module_id: int,
    payload: ModuleCreateRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    version_no: Annotated[int, Query(ge=1)],
) -> ApiResponse[ModuleDiffData]:
    """Compare a persisted module version with unsaved import content."""

    try:
        data = get_module_diff_preview(settings, module_id, version_no, payload)
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="比較対象のモジュール版が見つかりませんでした。",
        )

    return success_response(data, "取込内容との差分を取得しました。")


@router.get("/{module_id}/versions", response_model=ApiResponse[ModuleVersionListData])
def read_module_versions(
    module_id: int,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ModuleVersionListData]:
    """Return versions for one module."""

    try:
        data = list_module_versions(settings, module_id)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="モジュールが見つかりませんでした。",
        )

    return success_response(data, "モジュール版一覧を取得しました。")


@router.get("/{module_id}/versions/{version_no}/status", response_model=ApiResponse[ApprovalStatusDetailData])
def read_module_version_status(
    module_id: int,
    version_no: int,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ApprovalStatusDetailData]:
    """Return approval status detail for one module version."""

    try:
        data = get_module_version_status(settings, module_id, version_no)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="モジュール版が見つかりませんでした。",
        )

    return success_response(data, "モジュール版の承認状態を取得しました。")


@router.patch("/{module_id}/versions/{version_no}/status", response_model=ApiResponse[ApprovalStatusDetailData])
def patch_module_version_status(
    module_id: int,
    version_no: int,
    payload: ApprovalStatusUpdateRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ApprovalStatusDetailData]:
    """Update approval status for one module version."""

    try:
        data = update_module_version_status(
            settings,
            module_id,
            version_no,
            payload.status,
            payload.changed_by,
            payload.note,
        )
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="モジュール版が見つかりませんでした。",
        )

    return success_response(data, "モジュール版の承認状態を更新しました。")


@router.get("/{module_id}", response_model=ApiResponse[ModuleDetailData])
def read_module_detail(
    module_id: int,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    version_no: Annotated[int | None, Query(ge=1)] = None,
) -> ApiResponse[ModuleDetailData]:
    """Return module detail from PostgreSQL.

    Args:
        module_id: Target module identifier.
        settings: Application settings provided by dependency injection.

    Returns:
        Common response containing module detail data.

    Raises:
        HTTPException: If the module does not exist or the DB query fails.
    """

    try:
        data = get_module_detail(settings, module_id, version_no)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="モジュールが見つかりませんでした。",
        )

    return success_response(data, "モジュール詳細を取得しました。")


@router.get("/images/{module_row_image_id}", response_class=FileResponse)
def read_module_row_image(
    module_row_image_id: int,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> FileResponse:
    """Return an extracted module row image file."""

    try:
        image_metadata = get_module_row_image(settings, module_row_image_id)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if image_metadata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="画像が見つかりませんでした。",
        )

    image_file = _resolve_module_image_file(settings, image_metadata.image_path)
    if image_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="画像が見つかりませんでした。",
        )

    media_type, _ = mimetypes.guess_type(image_file.name)
    return FileResponse(
        path=image_file,
        media_type=media_type or "application/octet-stream",
        filename=image_file.name,
    )


@router.post(
    "/similarity-check",
    response_model=ApiResponse[ModuleSimilarityCheckData],
)
def check_module_similarity_resource(
    payload: ModuleCreateRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ModuleSimilarityCheckData]:
    """Return similar published modules before registration."""

    try:
        data = check_similar_modules(settings, payload)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "類似モジュールを確認しました。")


@router.post("", response_model=ApiResponse[ModuleDetailData], status_code=status.HTTP_201_CREATED)
def create_module_resource(
    payload: ModuleCreateRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    similarity_confirmation_token: Annotated[str | None, Query(max_length=4096)] = None,
) -> ApiResponse[ModuleDetailData] | JSONResponse:
    """Create a module, its first version, and module rows."""

    try:
        similarity_result = check_similar_modules(settings, payload)
        if not validate_similarity_confirmation_token(
            settings,
            similarity_result,
            similarity_confirmation_token,
        ):
            response = ApiResponse[ModuleSimilarityCheckData](
                result="error",
                data=similarity_result,
                message=(
                    "類似候補の確認が必要です。"
                    "最新の候補を確認してから登録を続けてください。"
                ),
            )
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=response.model_dump(mode="json"),
            )
        data = create_module(settings, payload)
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "モジュールを登録しました。")


@router.post("/import-sheet", response_model=ApiResponse[ModuleCreateRequest])
def normalize_module_sheet_resource(
    payload: ExcelImportSheetRequest,
) -> ApiResponse[ModuleCreateRequest]:
    """Normalize one Excel sheet worth of input into ``ModuleCreateRequest``.

    This is the thin Sprint 3 entry point before we add real multipart upload.
    It lets the frontend or tests submit one-sheet JSON and verify the helper
    output that will later feed the existing create API.
    """

    try:
        data = build_module_create_request_from_sheet_data(
            module_key=payload.module_key,
            module_name=payload.module_name,
            description=payload.description,
            change_note=payload.change_note,
            source_xlsx_path=payload.source_xlsx_path,
            source_sha256=payload.source_sha256,
            created_by=payload.created_by,
            device_header_cells=[header.model_dump() for header in payload.device_header_cells],
            row_cells=[row.model_dump() for row in payload.row_cells],
        )
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return success_response(data, "Excel取込プレビューを正規化しました。")


@router.post("/import", response_model=ApiResponse[ModuleCreateRequest])
def import_module_workbook_resource(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    payload: bytes = Body(),
    filename: Annotated[str, Query(min_length=1)] = "",
    created_by: Annotated[str | None, Query()] = None,
    sheet_name: Annotated[str | None, Query()] = None,
) -> ApiResponse[ModuleCreateRequest]:
    """Normalize one uploaded workbook into ``ModuleCreateRequest``.

    Sprint 3 first exposes raw binary upload so we can validate the workbook
    parser before wiring multipart upload in the UI.
    """

    try:
        data = build_module_create_request_from_workbook_bytes(
            workbook_bytes=payload,
            filename=filename,
            created_by=created_by,
            sheet_name=sheet_name,
            image_storage_dir=settings.module_image_storage_dir,
        )
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return success_response(data, "ワークブック取込結果を正規化しました。")
