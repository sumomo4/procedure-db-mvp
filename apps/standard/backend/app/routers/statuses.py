"""Approval status resource routes for Sprint 2 implementation."""

from fastapi import APIRouter

from app.core.responses import (
    ApiResponse,
    RouterEndpointData,
    RouterFoundationData,
    success_response,
)


router = APIRouter(prefix="/statuses", tags=["statuses"])


@router.get("/foundation", response_model=ApiResponse[RouterFoundationData])
def read_status_router_foundation() -> ApiResponse[RouterFoundationData]:
    """Return the approval status API router foundation status.

    Returns:
        Common response containing planned status endpoints.
    """

    data = RouterFoundationData(
        resource="statuses",
        sprint="Sprint 2",
        status="foundation-ready",
        planned_endpoints=[
            RouterEndpointData(method="GET", path="/api/v1/statuses", purpose="承認状態一覧取得"),
            RouterEndpointData(method="GET", path="/api/v1/statuses/{target_id}", purpose="対象別承認状態取得"),
            RouterEndpointData(method="PATCH", path="/api/v1/statuses/{target_id}", purpose="承認状態変更"),
        ],
    )
    return success_response(data, "Status router foundation is available.")
