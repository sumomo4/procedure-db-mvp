"""Module resource routes for Sprint 2 implementation."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApiResponse,
    ModuleDetailData,
    ModuleListData,
    RouterEndpointData,
    RouterFoundationData,
    success_response,
)
from app.db.modules import VALID_MODULE_STATUSES, get_module_detail, list_modules
from app.routers.health import get_app_settings


router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=ApiResponse[ModuleListData])
def read_modules(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    keyword: Annotated[str | None, Query(min_length=1)] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
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
            detail="status must be one of all, draft, published, archived.",
        )

    try:
        data = list_modules(
            settings,
            keyword=keyword,
            status_filter=normalized_status,
        )
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "Modules are available.")


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
    return success_response(data, "Module router foundation is available.")


@router.get("/{module_id}", response_model=ApiResponse[ModuleDetailData])
def read_module_detail(
    module_id: int,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
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
        data = get_module_detail(settings, module_id)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module was not found.",
        )

    return success_response(data, "Module detail is available.")
