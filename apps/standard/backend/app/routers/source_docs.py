"""Source document resource routes for Sprint 2 implementation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApiResponse,
    RouterEndpointData,
    RouterFoundationData,
    SourceDocCreateRequest,
    SourceDocDetailData,
    SourceDocListData,
    SourceDocUpdateRequest,
    success_response,
)
from app.db.source_docs import (
    VALID_SOURCE_DOC_STATUSES,
    create_source_doc,
    get_source_doc_detail,
    list_source_docs,
    update_source_doc,
)
from app.routers.health import get_app_settings


router = APIRouter(prefix="/source-docs", tags=["source-docs"])


@router.get("", response_model=ApiResponse[SourceDocListData])
def read_source_docs(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    keyword: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> ApiResponse[SourceDocListData]:
    """Return source document list from PostgreSQL."""

    normalized_status = status_filter.lower() if status_filter else None
    if normalized_status and normalized_status != "all" and normalized_status not in VALID_SOURCE_DOC_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be one of all, draft, published, archived.",
        )

    try:
        data = list_source_docs(
            settings,
            keyword=keyword,
            status_filter=normalized_status,
        )
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "原本一覧を取得しました。")


@router.get("/foundation", response_model=ApiResponse[RouterFoundationData])
def read_source_doc_router_foundation() -> ApiResponse[RouterFoundationData]:
    """Return the source document API router foundation status."""

    data = RouterFoundationData(
        resource="source-docs",
        sprint="Sprint 2",
        status="foundation-ready",
        planned_endpoints=[
            RouterEndpointData(method="GET", path="/api/v1/source-docs", purpose="原本一覧参照 / 検索"),
            RouterEndpointData(method="GET", path="/api/v1/source-docs/{source_doc_id}", purpose="原本詳細参照"),
            RouterEndpointData(method="POST", path="/api/v1/source-docs", purpose="原本作成"),
            RouterEndpointData(method="PUT", path="/api/v1/source-docs/{source_doc_id}", purpose="原本更新"),
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


@router.post("", response_model=ApiResponse[SourceDocDetailData], status_code=status.HTTP_201_CREATED)
def create_source_doc_resource(
    payload: SourceDocCreateRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocDetailData]:
    """Create a source document, its first version, and linked modules."""

    try:
        data = create_source_doc(settings, payload)
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
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[SourceDocDetailData]:
    """Update a source document and create its next version."""

    try:
        data = update_source_doc(settings, source_doc_id, payload)
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
