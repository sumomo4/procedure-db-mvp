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
    success_response,
)
from app.db.source_docs import (
    VALID_SOURCE_DOC_STATUSES,
    create_source_doc,
    get_source_doc_detail,
    list_source_docs,
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

    return success_response(data, "Source documents are available.")


@router.get("/foundation", response_model=ApiResponse[RouterFoundationData])
def read_source_doc_router_foundation() -> ApiResponse[RouterFoundationData]:
    """Return the source document API router foundation status."""

    data = RouterFoundationData(
        resource="source-docs",
        sprint="Sprint 2",
        status="foundation-ready",
        planned_endpoints=[
            RouterEndpointData(method="GET", path="/api/v1/source-docs", purpose="原本一覧取得 / 検索"),
            RouterEndpointData(method="GET", path="/api/v1/source-docs/{source_doc_id}", purpose="原本詳細取得"),
            RouterEndpointData(method="POST", path="/api/v1/source-docs", purpose="原本作成"),
            RouterEndpointData(method="PUT", path="/api/v1/source-docs/{source_doc_id}", purpose="原本更新"),
        ],
    )
    return success_response(data, "Source document router foundation is available.")


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
            detail="Source document was not found.",
        )

    return success_response(data, "Source document detail is available.")


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

    return success_response(data, "Source document was created.")
