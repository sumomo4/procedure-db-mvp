"""Common API response models and helpers."""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel


DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """Common API response envelope.

    Attributes:
        result: Processing result. Use ``success`` for normal responses and
            ``error`` for error responses.
        data: Response payload.
        message: User-facing message.
    """

    result: Literal["success", "error"]
    data: DataT | None = None
    message: str = ""


class HealthData(BaseModel):
    """Health check response payload.

    Attributes:
        service: API service name.
        environment: Application environment.
        status: Health status.
    """

    service: str
    environment: str
    status: Literal["ok"]


class DatabaseHealthData(BaseModel):
    """Database health check response payload.

    Attributes:
        database: Database name.
        host: Database host name.
        port: Database port number.
        status: Database connection status.
    """

    database: str
    host: str
    port: int
    status: Literal["ok"]


class RouterEndpointData(BaseModel):
    """Planned endpoint information for a Sprint 2 router.

    Attributes:
        method: HTTP method.
        path: Endpoint path.
        purpose: Endpoint purpose.
    """

    method: str
    path: str
    purpose: str


class RouterFoundationData(BaseModel):
    """Router foundation response payload.

    Attributes:
        resource: Resource name handled by the router.
        sprint: Sprint where the main implementation is planned.
        status: Current implementation status.
        planned_endpoints: Endpoints planned for the resource.
    """

    resource: str
    sprint: str
    status: Literal["foundation-ready"]
    planned_endpoints: list[RouterEndpointData]


def success_response(data: DataT, message: str = "") -> ApiResponse[DataT]:
    """Build a successful API response.

    Args:
        data: Response payload.
        message: User-facing message.

    Returns:
        Common success response.
    """

    return ApiResponse(result="success", data=data, message=message)


def error_response(message: str) -> ApiResponse[None]:
    """Build an error API response.

    Args:
        message: User-facing error message.

    Returns:
        Common error response.
    """

    return ApiResponse(result="error", data=None, message=message)
