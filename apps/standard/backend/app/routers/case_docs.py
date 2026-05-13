"""Case document generation routes for Sprint 4."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.case_doc_generation import XLSM_MEDIA_TYPE, build_case_doc_workbook_bytes
from app.core.responses import (
    ApiResponse,
    CaseDocGenerateRequest,
    CaseDocMasterOptionsData,
    CaseDocPlaceholderMappingListData,
    CaseDocResolveContextData,
    CaseDocResolveContextRequest,
    CaseDocUnitConfigListData,
    RouterEndpointData,
    RouterFoundationData,
    success_response,
)
from app.db.case_docs import (
    list_case_doc_buildings,
    list_case_doc_placeholder_mappings,
    list_case_doc_prefectures,
    list_case_doc_unit_configs,
    resolve_case_doc_context,
)
from app.db.source_docs import get_source_doc_detail
from app.routers.health import get_app_settings


router = APIRouter(prefix="/case-docs", tags=["case-docs"])


@router.get("/foundation", response_model=ApiResponse[RouterFoundationData])
def read_case_doc_router_foundation() -> ApiResponse[RouterFoundationData]:
    """Return the case document API router foundation status."""

    data = RouterFoundationData(
        resource="case-docs",
        sprint="Sprint 4",
        status="foundation-ready",
        planned_endpoints=[
            RouterEndpointData(
                method="GET",
                path="/api/v1/case-docs/master/prefectures",
                purpose="Case document prefecture master options.",
            ),
            RouterEndpointData(
                method="GET",
                path="/api/v1/case-docs/master/buildings",
                purpose="Case document building master options.",
            ),
            RouterEndpointData(
                method="GET",
                path="/api/v1/case-docs/master/unit-config",
                purpose="Case document unit configuration candidates.",
            ),
            RouterEndpointData(
                method="GET",
                path="/api/v1/case-docs/placeholders",
                purpose="Case document placeholder mappings used during generation.",
            ),
            RouterEndpointData(
                method="POST",
                path="/api/v1/case-docs/resolve-context",
                purpose="Resolve case document generation context without manual placeholder input.",
            ),
            RouterEndpointData(
                method="POST",
                path="/api/v1/case-docs/generate",
                purpose="Generate a case document from a source document and resolved context.",
            ),
        ],
    )
    return success_response(data, "Case document API foundation is ready.")


@router.get("/master/prefectures", response_model=ApiResponse[CaseDocMasterOptionsData])
def read_case_doc_prefectures(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[CaseDocMasterOptionsData]:
    """Return selectable prefectures for case document generation."""

    data = list_case_doc_prefectures(settings)
    return success_response(data, "Case document prefectures were retrieved.")


@router.get("/master/buildings", response_model=ApiResponse[CaseDocMasterOptionsData])
def read_case_doc_buildings(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    prefecture: Annotated[str, Query(min_length=1)],
) -> ApiResponse[CaseDocMasterOptionsData]:
    """Return selectable buildings for selected prefecture."""

    data = list_case_doc_buildings(settings, prefecture)
    return success_response(data, "Case document buildings were retrieved.")


@router.get("/master/unit-config", response_model=ApiResponse[CaseDocUnitConfigListData])
def read_case_doc_unit_configs(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
    prefecture: Annotated[str, Query(min_length=1)],
    building: Annotated[str, Query(min_length=1)],
) -> ApiResponse[CaseDocUnitConfigListData]:
    """Return unit configuration candidates for selected location."""

    data = list_case_doc_unit_configs(settings, prefecture, building)
    return success_response(data, "Case document unit configurations were retrieved.")


@router.get("/placeholders", response_model=ApiResponse[CaseDocPlaceholderMappingListData])
def read_case_doc_placeholder_mappings(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[CaseDocPlaceholderMappingListData]:
    """Return placeholder mappings used for case document generation."""

    try:
        data = list_case_doc_placeholder_mappings(settings)
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception
    return success_response(data, "Case document placeholder mappings were retrieved.")


@router.post("/resolve-context", response_model=ApiResponse[CaseDocResolveContextData])
def resolve_case_doc_generation_context(
    payload: CaseDocResolveContextRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[CaseDocResolveContextData]:
    """Resolve generation context without accepting manual placeholder values."""

    try:
        data = resolve_case_doc_context(settings, payload)
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    return success_response(data, "Case document context was resolved.")


@router.post("/generate")
def generate_case_doc(
    payload: CaseDocGenerateRequest,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> Response:
    """Generate a downloadable case document workbook."""

    try:
        context = resolve_case_doc_context(settings, payload)
    except ValueError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception

    try:
        source_doc = get_source_doc_detail(settings, payload.source_doc_id)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    if source_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="source document was not found.",
        )

    workbook_bytes = build_case_doc_workbook_bytes(context, source_doc)
    filename = f"case-doc-{payload.source_doc_id}-{context.unit_config.unit_config_id}.xlsm"
    return Response(
        content=workbook_bytes,
        media_type=XLSM_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
