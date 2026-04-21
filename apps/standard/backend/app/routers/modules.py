"""Module resource routes for Sprint 2 implementation."""

from fastapi import APIRouter

from app.core.responses import (
    ApiResponse,
    RouterEndpointData,
    RouterFoundationData,
    success_response,
)


router = APIRouter(prefix="/modules", tags=["modules"])


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
