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


class ModuleListItemData(BaseModel):
    """Module list item response payload.

    Attributes:
        module_id: Internal module identifier.
        module_key: Human-readable unique module key.
        module_name: Module display name.
        description: Optional module description.
        module_version_id: Internal module version identifier.
        version_no: Module version number.
        status: Current module version status.
        status_label: User-facing status label.
        row_count: Number of rows in the module version.
        first_work_text: First non-empty work text in module rows.
        source_xlsx_path: Source Excel path used during import.
        created_by: User who created the module version.
        updated_at: Last update date string.
    """

    module_id: int
    module_key: str
    module_name: str
    description: str | None
    module_version_id: int
    version_no: int
    status: Literal["draft", "published", "archived"]
    status_label: str
    row_count: int
    first_work_text: str | None
    source_xlsx_path: str | None
    created_by: str | None
    updated_at: str


class ModuleListData(BaseModel):
    """Module list response payload.

    Attributes:
        items: Module list items.
    """

    items: list[ModuleListItemData]


class ModuleRowData(BaseModel):
    """Module row response payload.

    Attributes:
        module_row_id: Internal module row identifier.
        row_order: Display order in the module version.
        row_type: Row type imported from the source module.
        major_no: Major procedure number.
        middle_no: Middle procedure number.
        minor_no: Minor procedure number.
        tech_doc_text: Technical document text.
        work_text: Work instruction text.
        expected_result: Expected result text.
        time_text: Time/check column text.
        window_text: Window column text.
        p_text: Prompt column text.
        command_text: Command column text.
        note: Optional note.
    """

    module_row_id: int
    row_order: int
    row_type: str
    major_no: str | None
    middle_no: str | None
    minor_no: str | None
    tech_doc_text: str | None
    work_text: str | None
    expected_result: str | None
    time_text: str | None
    window_text: str | None
    p_text: str | None
    command_text: str | None
    note: str | None


class ModuleDetailData(BaseModel):
    """Module detail response payload.

    Attributes:
        module_id: Internal module identifier.
        module_key: Human-readable unique module key.
        module_name: Module display name.
        description: Optional module description.
        module_version_id: Internal module version identifier.
        version_no: Module version number.
        status: Current module version status.
        status_label: User-facing status label.
        row_count: Number of rows in the module version.
        source_xlsx_path: Source Excel path used during import.
        created_by: User who created the module version.
        created_at: Creation date string.
        updated_at: Last update date string.
        rows: Rows included in the module version.
    """

    module_id: int
    module_key: str
    module_name: str
    description: str | None
    module_version_id: int
    version_no: int
    status: Literal["draft", "published", "archived"]
    status_label: str
    row_count: int
    source_xlsx_path: str | None
    created_by: str | None
    created_at: str
    updated_at: str
    rows: list[ModuleRowData]


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
