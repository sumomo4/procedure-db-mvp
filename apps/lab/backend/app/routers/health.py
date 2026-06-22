"""Health check routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import AppSettings, get_settings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import ApiResponse, DatabaseHealthData, HealthData, success_response
from app.db.connection import check_database_connection


router = APIRouter(prefix="/health", tags=["health"])


def get_app_settings() -> AppSettings:
    """Provide settings for FastAPI dependency injection.

    Returns:
        Application settings.
    """

    return get_settings()


@router.get("", response_model=ApiResponse[HealthData])
def read_health(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[HealthData]:
    """Return API health status.

    Args:
        settings: Application settings provided by dependency injection.

    Returns:
        Common response containing API health information.
    """

    data = HealthData(
        service=settings.service_name,
        environment=settings.app_env,
        status="ok",
    )
    return success_response(data, "API is available.")


@router.get("/db", response_model=ApiResponse[DatabaseHealthData])
def read_database_health(
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[DatabaseHealthData]:
    """Return PostgreSQL connection health status.

    Args:
        settings: Application settings provided by dependency injection.

    Returns:
        Common response containing PostgreSQL health information.

    Raises:
        HTTPException: If the PostgreSQL connection check fails.
    """

    try:
        data = check_database_connection(settings)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exception),
        ) from exception

    return success_response(data, "Database connection is available.")
