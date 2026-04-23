"""Approval status resource routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApiResponse,
    ApprovalStatusDetailData,
    ApprovalStatusListData,
    ApprovalStatusUpdateRequest,
    RouterEndpointData,
    RouterFoundationData,
    success_response,
)
from app.db.statuses import get_status_detail, list_statuses, update_status
from app.routers.health import get_app_settings


router = APIRouter(prefix="/statuses", tags=["statuses"])


@router.get("", response_model=ApiResponse[ApprovalStatusListData])
def read_statuses(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ApprovalStatusListData]:
    """Return approval status list from PostgreSQL."""

    try:
        data = list_statuses(settings)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "Approval statuses are available.")


@router.get("/foundation", response_model=ApiResponse[RouterFoundationData])
def read_status_router_foundation() -> ApiResponse[RouterFoundationData]:
    """Return the approval status API router foundation status."""

    data = RouterFoundationData(
        resource="statuses",
        sprint="Sprint 3",
        status="foundation-ready",
        planned_endpoints=[
            RouterEndpointData(method="GET", path="/api/v1/statuses", purpose="承認状態一覧取得"),
            RouterEndpointData(method="GET", path="/api/v1/statuses/{target_id}", purpose="対象別承認状態取得"),
            RouterEndpointData(method="PATCH", path="/api/v1/statuses/{target_id}", purpose="承認状態変更"),
        ],
    )
    return success_response(data, "Status router foundation is available.")


@router.get("/{target_id}", response_model=ApiResponse[ApprovalStatusDetailData])
def read_status_detail(
    target_id: int,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ApprovalStatusDetailData]:
    """Return one approval target detail from PostgreSQL."""

    try:
        data = get_status_detail(settings, target_id)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval target was not found.",
        )

    return success_response(data, "Approval status detail is available.")


@router.patch("/{target_id}", response_model=ApiResponse[ApprovalStatusDetailData])
def patch_status_detail(
    target_id: int,
    payload: ApprovalStatusUpdateRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[ApprovalStatusDetailData]:
    """Update one approval target status."""

    try:
        data = update_status(settings, target_id, payload.status)
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
            detail="Approval target was not found.",
        )

    return success_response(data, "Approval status was updated.")
