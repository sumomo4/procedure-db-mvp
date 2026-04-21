"""Source document resource routes for Sprint 2 implementation."""

from fastapi import APIRouter

from app.core.responses import (
    ApiResponse,
    RouterEndpointData,
    RouterFoundationData,
    success_response,
)


router = APIRouter(prefix="/source-docs", tags=["source-docs"])


@router.get("/foundation", response_model=ApiResponse[RouterFoundationData])
def read_source_doc_router_foundation() -> ApiResponse[RouterFoundationData]:
    """Return the source document API router foundation status.

    Returns:
        Common response containing planned source document endpoints.
    """

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
