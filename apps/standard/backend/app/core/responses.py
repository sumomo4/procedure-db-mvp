"""Common API response models and helpers."""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field


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
        indent_level: Excel-derived indentation level for the work column.
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
    indent_level: int | None
    expected_result: str | None
    time_text: str | None
    window_text: str | None
    p_text: str | None
    command_text: str | None
    note: str | None
    device_entries: list["ModuleRowDeviceEntryData"] = Field(default_factory=list)


class ModuleRowDeviceEntryData(BaseModel):
    """Device-specific command columns for one module row."""

    slot_no: int = Field(ge=1, le=20)
    time_text: str | None = None
    window_text: str | None = None
    p_text: str | None = None
    command_text: str | None = None


class ModuleDeviceHeaderData(BaseModel):
    """Device-specific header columns for one module version."""

    slot_no: int = Field(ge=1, le=20)
    header_time_text: str | None = None
    target_text: str | None = None
    p_text: str | None = None
    target_device_text: str | None = None


class ModuleCreateRowDeviceEntryInput(BaseModel):
    """Device-specific input payload for one module row."""

    slot_no: int = Field(ge=1, le=20)
    time_text: str | None = None
    window_text: str | None = None
    p_text: str | None = None
    command_text: str | None = None


class ModuleCreateDeviceHeaderInput(BaseModel):
    """Device-specific header input payload for a module version."""

    slot_no: int = Field(ge=1, le=20)
    header_time_text: str | None = None
    target_text: str | None = None
    p_text: str | None = None
    target_device_text: str | None = None


class ModuleCreateRowInput(BaseModel):
    """Module row input payload for create API."""

    row_order: int = Field(gt=0)
    row_type: Literal["header", "step", "meta", "spacer"]
    major_no: str | None = None
    middle_no: str | None = None
    minor_no: str | None = None
    tech_doc_text: str | None = None
    work_text: str | None = None
    indent_level: int | None = Field(default=None, ge=0, le=3)
    expected_result: str | None = None
    time_text: str | None = None
    window_text: str | None = None
    p_text: str | None = None
    command_text: str | None = None
    note: str | None = None
    device_entries: list[ModuleCreateRowDeviceEntryInput] = Field(default_factory=list)


class ModuleCreateRequest(BaseModel):
    """Module create request payload."""

    module_key: str | None = None
    module_name: str = Field(min_length=1)
    description: str | None = None
    change_note: str | None = None
    source_xlsx_path: str | None = None
    source_sha256: str | None = None
    created_by: str | None = None
    header_time_text: str | None = None
    target_text: str | None = None
    common_p_text: str | None = None
    target_device_text: str | None = None
    device_headers: list[ModuleCreateDeviceHeaderInput] = Field(default_factory=list)
    rows: list[ModuleCreateRowInput] = Field(min_length=1)


class ExcelImportSheetDeviceHeaderInput(BaseModel):
    """Normalized device header cells extracted from one Excel sheet."""

    slot_no: int = Field(ge=1, le=20)
    header_time_text: str | None = None
    target_text: str | None = None
    p_text: str | None = None
    target_device_text: str | None = None


class ExcelImportSheetRowDeviceEntryInput(BaseModel):
    """Device-specific command cells extracted from one Excel row."""

    slot_no: int = Field(ge=1, le=20)
    time_text: str | None = None
    window_text: str | None = None
    p_text: str | None = None
    command_text: str | None = None


class ExcelImportSheetRowInput(BaseModel):
    """One Excel row expressed with the minimum tracked cell set."""

    A: str | None = None
    B: str | None = None
    C: str | None = None
    D: str | None = None
    E: str | None = None
    F: str | None = None
    G: str | None = None
    H: str | None = None
    I: str | None = None
    device_entries: list[ExcelImportSheetRowDeviceEntryInput] = Field(default_factory=list)


class ExcelImportSheetRequest(BaseModel):
    """One-sheet Excel import payload normalized before real file upload."""

    module_key: str | None = None
    module_name: str = Field(min_length=1)
    description: str | None = None
    change_note: str | None = None
    source_xlsx_path: str | None = None
    source_sha256: str | None = None
    created_by: str | None = None
    device_header_cells: list[ExcelImportSheetDeviceHeaderInput] = Field(default_factory=list)
    row_cells: list[ExcelImportSheetRowInput] = Field(min_length=1)


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
    header_time_text: str | None
    target_text: str | None
    common_p_text: str | None
    target_device_text: str | None
    device_headers: list[ModuleDeviceHeaderData] = Field(default_factory=list)
    created_at: str
    updated_at: str
    rows: list[ModuleRowData]


class SourceDocListItemData(BaseModel):
    """Source document list item response payload.

    Attributes:
        source_doc_id: Internal source document identifier.
        source_doc_key: Human-readable unique source document key.
        source_doc_name: Source document display name.
        description: Optional source document description.
        source_doc_version_id: Internal source document version identifier.
        version_no: Source document version number.
        status: Current source document version status.
        status_label: User-facing status label.
        module_count: Number of linked modules.
        enabled_module_count: Number of enabled linked modules.
        module_names: Linked module display names in item order.
        created_by: User who created the source document version.
        updated_at: Last update date string.
    """

    source_doc_id: int
    source_doc_key: str
    source_doc_name: str
    description: str | None
    source_doc_version_id: int
    version_no: int
    status: Literal["draft", "published", "archived"]
    status_label: str
    module_count: int
    enabled_module_count: int
    module_names: list[str]
    created_by: str | None
    updated_at: str


class SourceDocListData(BaseModel):
    """Source document list response payload."""

    items: list[SourceDocListItemData]


class SourceDocCreateItemInput(BaseModel):
    """Linked module input payload for source document create API."""

    module_id: int = Field(gt=0)
    enabled: bool = True
    item_order: int | None = Field(default=None, gt=0)


class SourceDocCreateRequest(BaseModel):
    """Source document create request payload."""

    source_doc_key: str | None = None
    source_doc_name: str = Field(min_length=1)
    description: str | None = None
    change_note: str | None = None
    created_by: str | None = None
    items: list[SourceDocCreateItemInput] = Field(min_length=1)


class SourceDocUpdateRequest(BaseModel):
    """Source document update request payload."""

    source_doc_key: str | None = None
    source_doc_name: str = Field(min_length=1)
    description: str | None = None
    change_note: str | None = None
    created_by: str | None = None
    items: list[SourceDocCreateItemInput] = Field(min_length=1)


class SourceDocModuleItemData(BaseModel):
    """Linked module item included in a source document detail response."""

    blueprint_item_id: int
    item_order: int
    enabled: bool
    module_id: int
    module_key: str
    module_name: str
    module_version_id: int
    module_version_no: int
    module_status: Literal["draft", "published", "archived"]
    module_status_label: str
    rows: list[ModuleRowData]


class SourceDocDetailData(BaseModel):
    """Source document detail response payload."""

    source_doc_id: int
    source_doc_key: str
    source_doc_name: str
    description: str | None
    source_doc_version_id: int
    version_no: int
    status: Literal["draft", "published", "archived"]
    status_label: str
    change_note: str | None
    module_count: int
    enabled_module_count: int
    created_by: str | None
    created_at: str
    updated_at: str
    items: list[SourceDocModuleItemData]


class ApprovalTransitionData(BaseModel):
    """Allowed approval transition for a target."""

    to_status: Literal["draft", "published", "archived"]
    to_status_label: str
    action_label: str


class ApprovalStatusListItemData(BaseModel):
    """Approval status list item response payload."""

    target_id: int
    target_key: str
    target_name: str
    target_type: Literal["source-doc"]
    version_no: int
    status: Literal["draft", "published", "archived"]
    status_label: str
    next_action: str
    module_count: int
    enabled_module_count: int
    created_by: str | None
    updated_at: str


class ApprovalStatusListData(BaseModel):
    """Approval status list response payload."""

    items: list[ApprovalStatusListItemData]


class ApprovalStatusDetailData(BaseModel):
    """Approval status detail response payload."""

    target_id: int
    target_key: str
    target_name: str
    target_type: Literal["source-doc"]
    version_no: int
    status: Literal["draft", "published", "archived"]
    status_label: str
    next_action: str
    module_count: int
    enabled_module_count: int
    module_names: list[str]
    description: str | None
    change_note: str | None
    created_by: str | None
    updated_at: str
    allowed_transitions: list[ApprovalTransitionData]


class ApprovalStatusUpdateRequest(BaseModel):
    """Approval status update request payload."""

    status: Literal["draft", "published", "archived"]


class CaseDocMasterOptionData(BaseModel):
    """Selectable master option used by the case document workflow."""

    value: str
    label: str


class CaseDocMasterOptionsData(BaseModel):
    """List of selectable master options."""

    items: list[CaseDocMasterOptionData]


class CaseDocUnitConfigItemData(BaseModel):
    """Unit configuration candidate resolved from Access-derived data."""

    unit_config_id: str
    fs_cluster_name: str
    block: str
    prefecture: str
    building: str


class CaseDocUnitConfigListData(BaseModel):
    """Unit configuration candidates for selected location."""

    items: list[CaseDocUnitConfigItemData]


class CaseDocResolveContextRequest(BaseModel):
    """Request payload for resolving case document generation context."""

    source_doc_id: int = Field(gt=0)
    prefecture: str = Field(min_length=1)
    building: str = Field(min_length=1)
    fs_cluster_name: str | None = None
    block: str | None = None
    unit_config_id: str | None = None
    target_slot_key: str | None = None


class CaseDocHostAssignmentData(BaseModel):
    """Device host assignment resolved from the unit configuration."""

    slot_key: str
    device_type: str
    system: str | None = None
    host_name: str


class CaseDocCommonValueData(BaseModel):
    """Common value resolved without manual input."""

    key: str
    value: str
    source_table: str
    source_column: str
    source: str


class CaseDocResolvedPlaceholderData(BaseModel):
    """Placeholder resolution result for preview before generation."""

    placeholder: str
    value: str
    source_table: str
    source_column: str
    host_name: str | None = None


class CaseDocResolveContextData(BaseModel):
    """Resolved context used to generate a case document."""

    source_doc_id: int
    unit_config: CaseDocUnitConfigItemData
    target_assignment: CaseDocHostAssignmentData
    host_assignments: list[CaseDocHostAssignmentData]
    common_values: list[CaseDocCommonValueData]
    resolved_placeholders: list[CaseDocResolvedPlaceholderData]


class CaseDocGenerateRequest(CaseDocResolveContextRequest):
    """Request payload for case document generation."""


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
