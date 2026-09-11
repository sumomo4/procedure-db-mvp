"""Source document resource routes for Sprint 2 implementation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApiResponse,
    RouterEndpointData,
    RouterFoundationData,
    SourceDocCancellationData,
    SourceDocCancellationRequest,
    SourceDocCreateRequest,
    SourceDocDetailData,
    SourceDocListData,
    SourceDocTagDeleteRequest,
    SourceDocTagMoveRequest,
    SourceDocTagRenameRequest,
    SourceDocUpdateRequest,
    success_response,
)
from app.db.source_docs import (
    VALID_SOURCE_DOC_STATUSES,
    add_source_docs_to_tag,
    cancel_source_doc_registration,
    create_source_doc,
    delete_source_doc_tag,
    get_source_doc_detail,
    list_source_docs,
    rename_source_doc_tag,
    update_source_doc,
)
from app.routers.health import get_app_settings
from app.core.security import CurrentUser


router = APIRouter(prefix="/source-docs", tags=["source-docs"])


@router.get("", response_model=ApiResponse[SourceDocListData])
def read_source_docs(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    keyword: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    tag_paths: Annotated[list[str] | None, Query(alias="tag_path", min_length=1)] = None,
    created_by: Annotated[str | None, Query(min_length=1)] = None,
    updated_from: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    updated_to: Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")] = None,
    module_name: Annotated[str | None, Query(min_length=1)] = None,
    sort: Annotated[str | None, Query(pattern=r"^(key_asc|key_desc|updated_desc|updated_asc|status_asc)$")] = None,
) -> ApiResponse[SourceDocListData]:
    """Return source document list from PostgreSQL."""

    normalized_status = status_filter.lower() if status_filter else None
    if normalized_status and normalized_status != "all" and normalized_status not in VALID_SOURCE_DOC_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be one of all, draft, review_requested, returned, published, archived.",
        )

    try:
        data = list_source_docs(
            settings,
            keyword=keyword,
            status_filter=normalized_status,
            tag_paths=tag_paths,
            created_by=created_by,
            updated_from=updated_from,
            updated_to=updated_to,
            module_name=module_name,
            sort=sort,
        )
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "原本一覧を取得しました。")


@router.patch("/tags", response_model=ApiResponse[SourceDocListData])
def rename_source_doc_tag_path(
    request: SourceDocTagRenameRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocListData]:
    """Rename a source document tag path."""

    current_tag = request.current_tag_path.strip()
    new_tag = request.new_tag_path.strip()
    if not current_tag or not new_tag:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tag paths must not be empty.")

    try:
        data = rename_source_doc_tag(settings, current_tag, new_tag)
    except DatabaseConnectionError as exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exception)) from exception

    return success_response(data, "タグ名を変更しました。")


@router.delete("/tags", response_model=ApiResponse[SourceDocListData])
def delete_source_doc_tag_path(
    request: SourceDocTagDeleteRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocListData]:
    """Delete a source document tag and apply the uncategorized fallback."""

    target_tag = request.tag_path.strip()
    if not target_tag:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tag_path must not be empty.")
    if target_tag == "未分類":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uncategorized tag cannot be deleted.",
        )

    try:
        data = delete_source_doc_tag(settings, target_tag)
    except DatabaseConnectionError as exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exception)) from exception

    return success_response(data, "タグを削除しました。タグがなくなった原本は未分類へ移動しました。")


@router.patch("/tags/source-docs", response_model=ApiResponse[SourceDocListData])
def add_selected_source_docs_to_tag(
    request: SourceDocTagMoveRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocListData]:
    """Add selected source documents to a tag path."""

    target_tag = request.tag_path.strip()
    if not request.source_doc_ids or not target_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_doc_ids and tag_path are required.",
        )

    try:
        data = add_source_docs_to_tag(settings, request.source_doc_ids, target_tag)
    except DatabaseConnectionError as exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exception)) from exception

    return success_response(data, "選択した原本へタグを追加しました。")


@router.get("/foundation", response_model=ApiResponse[RouterFoundationData])
def read_source_doc_router_foundation() -> ApiResponse[RouterFoundationData]:
    """Return the source document API router foundation status."""

    data = RouterFoundationData(
        resource="source-docs",
        sprint="Sprint 2",
        status="foundation-ready",
        planned_endpoints=[
            RouterEndpointData(method="GET", path="/api/v1/source-docs", purpose="原本一覧参照 / 検索"),
            RouterEndpointData(method="PATCH", path="/api/v1/source-docs/tags", purpose="原本タグ名変更"),
            RouterEndpointData(method="DELETE", path="/api/v1/source-docs/tags", purpose="原本タグ削除"),
            RouterEndpointData(method="PATCH", path="/api/v1/source-docs/tags/source-docs", purpose="原本タグ追加"),
            RouterEndpointData(method="GET", path="/api/v1/source-docs/{source_doc_id}", purpose="原本詳細参照"),
            RouterEndpointData(method="POST", path="/api/v1/source-docs", purpose="原本作成"),
            RouterEndpointData(method="PUT", path="/api/v1/source-docs/{source_doc_id}", purpose="原本更新"),
            RouterEndpointData(method="DELETE", path="/api/v1/source-docs/{source_doc_id}", purpose="原本登録取消"),
        ],
    )
    return success_response(data, "原本 API 構成情報を取得しました。")


@router.get("/{source_doc_id}", response_model=ApiResponse[SourceDocDetailData])
def read_source_doc_detail(
    source_doc_id: int,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocDetailData]:
    """Return source document detail from PostgreSQL."""

    try:
        data = get_source_doc_detail(settings, source_doc_id)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="原本が見つかりませんでした。",
        )

    return success_response(data, "原本詳細を取得しました。")


@router.delete("/{source_doc_id}", response_model=ApiResponse[SourceDocCancellationData])
def cancel_source_doc_registration_resource(
    source_doc_id: int,
    payload: SourceDocCancellationRequest,
    current_user: CurrentUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocCancellationData]:
    """Logically cancel an accidental, unused initial draft registration."""

    try:
        data = cancel_source_doc_registration(
            settings,
            source_doc_id,
            current_user.display_name,
            payload.reason,
            payload.source_doc_key_confirmation,
        )
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
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
            detail="原本が見つかりませんでした。",
        )

    return success_response(data, "原本登録を取り消しました。")


@router.post("", response_model=ApiResponse[SourceDocDetailData], status_code=status.HTTP_201_CREATED)
def create_source_doc_resource(
    payload: SourceDocCreateRequest,
    current_user: CurrentUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocDetailData]:
    """Create a source document, its first version, and linked modules."""

    try:
        authenticated_payload = payload.model_copy(update={"created_by": current_user.display_name})
        data = create_source_doc(settings, authenticated_payload)
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

    return success_response(data, "原本を作成しました。")


@router.put("/{source_doc_id}", response_model=ApiResponse[SourceDocDetailData])
def update_source_doc_resource(
    source_doc_id: int,
    payload: SourceDocUpdateRequest,
    current_user: CurrentUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocDetailData]:
    """Update a source document and create its next version."""

    try:
        authenticated_payload = payload.model_copy(update={"created_by": current_user.display_name})
        data = update_source_doc(settings, source_doc_id, authenticated_payload)
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
            detail="原本が見つかりませんでした。",
        )

    return success_response(data, "原本を更新しました。")
