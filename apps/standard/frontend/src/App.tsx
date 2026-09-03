import { NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Fragment, useEffect, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { DevicePager, PreviewFrame, PreviewOverlay } from "./previewUi";

type Status = "Draft" | "approval" | "archive";

type AuthRole = "member" | "approver" | "admin";

type AuthUser = {
  username: string;
  displayName: string;
  role: AuthRole;
};

const AUTH_STORAGE_KEY = "mvpAuthUser";

const demoUsers: Record<string, AuthUser & { password: string }> = {
  member: {
    username: "member",
    password: "password",
    displayName: "メンバーユーザー",
    role: "member",
  },
  approver: {
    username: "approver",
    password: "password",
    displayName: "承認者ユーザー",
    role: "approver",
  },
  admin: {
    username: "admin",
    password: "admin",
    displayName: "管理者ユーザー",
    role: "admin",
  },
};

function getStoredAuthUser(): AuthUser | null {
  const rawUser = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (rawUser === null) {
    return null;
  }

  try {
    const parsedUser = JSON.parse(rawUser) as Partial<AuthUser>;
    if (
      typeof parsedUser.username === "string" &&
      typeof parsedUser.displayName === "string" &&
      (parsedUser.role === "member" || parsedUser.role === "approver" || parsedUser.role === "admin")
    ) {
      return {
        username: parsedUser.username,
        displayName: parsedUser.displayName,
        role: parsedUser.role,
      };
    }
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  return null;
}

function saveAuthUser(user: AuthUser): void {
  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
}

function clearAuthUser(): void {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

function getAuthRoleLabel(role: AuthRole): string {
  if (role === "admin") {
    return "管理者";
  }

  return role === "approver" ? "承認者" : "メンバー";
}

function getAuthRoleDescription(role: AuthRole): string {
  if (role === "admin") {
    return "プレースホルダ設定など、管理者向けの設定を確認・変更できます。";
  }

  return role === "approver"
    ? "承認依頼中の確認、差戻し、承認、保管を実行できます。"
    : "作成中または差戻し済みの原本・モジュールに対して承認依頼を実行できます。";
}

type ModuleRow = {
  id: string;
  name: string;
  category: string;
  owner: string;
  updatedAt: string;
  status: Status;
  version: string;
};

type ApiResult = "success" | "error";

type HealthData = {
  service: string;
  environment: string;
  status: "ok";
};

type DatabaseHealthData = {
  database: string;
  host: string;
  port: number;
  status: "ok";
};

type ModuleApiStatus = "draft" | "review_requested" | "returned" | "published" | "archived";

type ModuleListItemData = {
  module_id: number;
  module_key: string;
  module_name: string;
  description: string | null;
  folder_path: string;
  folder_paths?: string[];
  module_version_id: number;
  version_no: number;
  version_major: number;
  version_minor: number;
  version_label: string;
  status: ModuleApiStatus;
  status_label: string;
  row_count: number;
  first_work_text: string | null;
  source_xlsx_path: string | null;
  created_by: string | null;
  updated_at: string;
};

type ModuleListData = {
  items: ModuleListItemData[];
  folders: string[];
};

type ModuleVersionListItemData = {
  module_version_id: number;
  version_no: number;
  version_major: number;
  version_minor: number;
  version_label: string;
  status: ModuleApiStatus;
  status_label: string;
  row_count: number;
  source_xlsx_path: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

type ModuleVersionListData = {
  module_id: number;
  module_key: string;
  module_name: string;
  items: ModuleVersionListItemData[];
};

type ModuleDetailRowData = {
  module_row_id: number;
  row_order: number;
  row_type: string;
  major_no: string | null;
  middle_no: string | null;
  minor_no: string | null;
  tech_doc_text: string | null;
  work_text: string | null;
  indent_level: number | null;
  expected_result: string | null;
  time_text: string | null;
  window_text: string | null;
  p_text: string | null;
  command_text: string | null;
  note: string | null;
  device_entries: ModuleRowDeviceEntryData[];
  images: ModuleRowImageData[];
};

type ModuleRowImageData = {
  module_row_image_id?: number;
  image_key: string;
  image_path: string;
  anchor_cell: string;
  offset_x_px: number;
  offset_y_px: number;
  width_px: number | null;
  height_px: number | null;
  image_order: number;
};

type ModuleRowDeviceEntryData = {
  slot_no: number;
  time_text: string | null;
  window_text: string | null;
  p_text: string | null;
  command_text: string | null;
};

type ModuleDeviceHeaderData = {
  slot_no: number;
  header_time_text: string | null;
  target_text: string | null;
  p_text: string | null;
  target_device_text: string | null;
};

type ModuleDetailData = {
  module_id: number;
  module_key: string;
  module_name: string;
  description: string | null;
  module_version_id: number;
  version_no: number;
  version_major: number;
  version_minor: number;
  version_label: string;
  status: ModuleApiStatus;
  status_label: string;
  row_count: number;
  source_xlsx_path: string | null;
  created_by: string | null;
  header_time_text: string | null;
  target_text: string | null;
  common_p_text: string | null;
  target_device_text: string | null;
  device_headers: ModuleDeviceHeaderData[];
  created_at: string;
  updated_at: string;
  rows: ModuleDetailRowData[];
};

type ApiResponse<TData> = {
  result: ApiResult;
  data: TData | null;
  message: string;
};

type HealthCheckState = {
  status: "checking" | "available" | "unavailable";
  primary: string;
  secondary: string;
  message: string;
};

type ModuleListState = {
  status: "loading" | "available" | "unavailable";
  items: ModuleListItemData[];
  folders?: string[];
  message: string;
};

type ModuleFolderMoveState = {
  status: "idle" | "submitting" | "success" | "error";
  message: string;
};

type ModuleFolderRenameState = {
  status: "idle" | "submitting" | "success" | "error";
  message: string;
};

type ModuleFolderTreeItem = {
  path: string;
  label: string;
  depth: number;
  hasDirectModule: boolean;
};

type ModuleDetailState = {
  status: "loading" | "available" | "unavailable";
  item: ModuleDetailData | null;
  message: string;
};

type ModuleVersionListState = {
  status: "idle" | "loading" | "available" | "unavailable";
  items: ModuleVersionListItemData[];
  message: string;
};

type ModuleDiffSummaryData = {
  added_count: number;
  removed_count: number;
  changed_count: number;
  unchanged_count: number;
};

type ModuleDiffRowData = {
  status: "added" | "removed" | "changed" | "unchanged";
  row_key: string;
  before: ModuleDetailRowData | null;
  after: ModuleDetailRowData | null;
  changed_fields: string[];
  similarity: number | null;
};

type ModuleDiffData = {
  module_id: number;
  module_key: string;
  module_name: string;
  from_version: number;
  to_version: number;
  summary: ModuleDiffSummaryData;
  rows: ModuleDiffRowData[];
};

type ModuleDiffState = {
  status: "idle" | "loading" | "available" | "unavailable";
  item: ModuleDiffData | null;
  message: string;
};

type ModuleSimilarityScoreBreakdownData = {
  work_text: number | null;
  expected_result: number | null;
  command: number | null;
  name: number | null;
  structure: number | null;
  device_header: number | null;
};

type ModuleSimilarityCandidateData = {
  module_id: number;
  module_key: string;
  module_name: string;
  module_version_id: number;
  version_no: number;
  version_label: string;
  status: "published";
  similarity: number;
  exact_match: boolean;
  image_metadata_match: boolean;
  score_breakdown: ModuleSimilarityScoreBreakdownData;
  matched_fields: string[];
};

type ModuleSimilarityCheckData = {
  threshold: number;
  checked_count: number;
  candidate_count: number;
  exact_match: boolean;
  input_sha256: string;
  candidate_set_sha256: string;
  confirmation_token: string | null;
  candidates: ModuleSimilarityCandidateData[];
};

type ModuleSimilarityCheckState = {
  status: "idle" | "submitting" | "success" | "error";
  item: ModuleSimilarityCheckData | null;
  message: string;
};

type ModuleSimilarityDiffDownloadState = {
  status: "idle" | "loading" | "success" | "error";
  candidateId: number | null;
  message: string;
};

type ModuleCreateState = {
  status: "idle" | "submitting" | "success" | "error";
  item: ModuleDetailData | null;
  message: string;
};

type ModuleImportPreviewDeviceHeaderData = {
  slot_no: number;
  header_time_text: string | null;
  target_text: string | null;
  p_text: string | null;
  target_device_text: string | null;
};

type ModuleImportPreviewRowDeviceEntryData = {
  slot_no: number;
  time_text: string | null;
  window_text: string | null;
  p_text: string | null;
  command_text: string | null;
};

type ModuleImportPreviewRowData = {
  row_order: number;
  row_type: string;
  major_no: string | null;
  middle_no: string | null;
  minor_no: string | null;
  tech_doc_text: string | null;
  work_text: string | null;
  indent_level: number | null;
  expected_result: string | null;
  time_text: string | null;
  window_text: string | null;
  p_text: string | null;
  command_text: string | null;
  note: string | null;
  device_entries: ModuleImportPreviewRowDeviceEntryData[];
  images: ModuleRowImageData[];
};

type ModuleImportPreviewData = {
  module_key: string | null;
  module_name: string;
  description: string | null;
  change_note: string | null;
  source_xlsx_path: string | null;
  source_sha256: string | null;
  created_by: string | null;
  header_time_text: string | null;
  target_text: string | null;
  common_p_text: string | null;
  target_device_text: string | null;
  device_headers: ModuleImportPreviewDeviceHeaderData[];
  rows: ModuleImportPreviewRowData[];
};

type ModuleImportPreviewState = {
  status: "idle" | "submitting" | "success" | "error";
  item: ModuleImportPreviewData | null;
  message: string;
};

type ModuleRegisterRowType = "header" | "step" | "meta" | "spacer";

type ModuleRegisterRowDraft = {
  rowId: number;
  rowType: ModuleRegisterRowType;
  indentLevel: number;
  majorNo: string;
  middleNo: string;
  minorNo: string;
  techDocText: string;
  workText: string;
  expectedResult: string;
  deviceEntries: ModuleRegisterDeviceEntryDraft[];
  images: ModuleRowImageData[];
};

type ModuleRegisterDeviceHeaderDraft = {
  slotNo: number;
  headerTimeText: string;
  targetText: string;
  pText: string;
  targetDeviceText: string;
};

type ModuleRegisterDeviceEntryDraft = {
  slotNo: number;
  timeText: string;
  windowText: string;
  pText: string;
  commandText: string;
};

type SourceDocApiStatus = ModuleApiStatus;

type SourceDocListItemData = {
  source_doc_id: number;
  source_doc_key: string;
  source_doc_name: string;
  description: string | null;
  source_doc_version_id: number;
  version_no: number;
  version_major: number;
  version_minor: number;
  version_label: string;
  status: SourceDocApiStatus;
  status_label: string;
  module_count: number;
  enabled_module_count: number;
  module_names: string[];
  created_by: string | null;
  updated_at: string;
};

type SourceDocListData = {
  items: SourceDocListItemData[];
};

type SourceDocModuleItemData = {
  blueprint_item_id: number;
  item_order: number;
  enabled: boolean;
  module_id: number;
  module_key: string;
  module_name: string;
  module_version_id: number;
  module_version_no: number;
  module_status: ModuleApiStatus;
  module_status_label: string;
  rows: ModuleDetailRowData[];
};

type SourceDocDetailData = {
  source_doc_id: number;
  source_doc_key: string;
  source_doc_name: string;
  description: string | null;
  source_doc_version_id: number;
  version_no: number;
  version_major: number;
  version_minor: number;
  version_label: string;
  status: SourceDocApiStatus;
  status_label: string;
  change_note: string | null;
  module_count: number;
  enabled_module_count: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  items: SourceDocModuleItemData[];
};

type SourceDocListState = {
  status: "loading" | "available" | "unavailable";
  items: SourceDocListItemData[];
  message: string;
};

type SourceDocDetailState = {
  status: "loading" | "available" | "unavailable";
  item: SourceDocDetailData | null;
  message: string;
};

type SourceDocFormLoadState = {
  status: "idle" | "loading" | "ready" | "error";
  message: string;
};


type SourceDocCreateState = {
  status: "idle" | "submitting" | "success" | "error";
  item: SourceDocDetailData | null;
  message: string;
};

type SourceDocCreateItemDraft = {
  rowId: number;
  moduleId: string;
  enabled: boolean;
};



type CaseDocMasterOptionData = {
  value: string;
  label: string;
};

type CaseDocMasterOptionsData = {
  items: CaseDocMasterOptionData[];
};

type CaseDocUnitConfigItemData = {
  unit_config_id: string;
  fs_cluster_name: string;
  block: string;
  prefecture: string;
  building: string;
};

type CaseDocUnitConfigListData = {
  items: CaseDocUnitConfigItemData[];
};

type CaseDocHostAssignmentData = {
  slot_key: string;
  device_type: string;
  system: string | null;
  host_name: string;
};

type CaseDocTargetDeviceSlotData = {
  excel_no: number;
  slot_key: string;
  device_type: string;
  system: string | null;
  host_name: string;
};

type CaseDocCommonValueData = {
  key: string;
  value: string;
  source_table: string;
  source_column: string;
  source: string;
};

type CaseDocResolvedPlaceholderData = {
  placeholder: string;
  value: string;
  source_table: string;
  source_column: string;
  host_name: string | null;
};

type CaseDocResolveContextData = {
  source_doc_id: number;
  unit_config: CaseDocUnitConfigItemData;
  target_assignment: CaseDocHostAssignmentData;
  target_assignments: CaseDocHostAssignmentData[];
  target_device_slots: CaseDocTargetDeviceSlotData[];
  host_assignments: CaseDocHostAssignmentData[];
  common_values: CaseDocCommonValueData[];
  resolved_placeholders: CaseDocResolvedPlaceholderData[];
};

type CaseDocOptionLoadState = {
  status: "loading" | "available" | "unavailable";
  items: CaseDocMasterOptionData[];
  message: string;
};

type CaseDocUnitConfigLoadState = {
  status: "idle" | "loading" | "available" | "unavailable";
  items: CaseDocUnitConfigItemData[];
  message: string;
};

type CaseDocResolveState = {
  status: "idle" | "submitting" | "success" | "error";
  item: CaseDocResolveContextData | null;
  message: string;
};

type CaseDocGenerateState = {
  status: "idle" | "submitting" | "success" | "error";
  filename: string | null;
  message: string;
};

type CaseDocExecutionStatus = "pending" | "checked" | "skipped";

type CaseDocExecutionHistoryData = {
  history_id: number;
  from_status: CaseDocExecutionStatus;
  to_status: CaseDocExecutionStatus;
  changed_at: string;
  changed_by: string | null;
  note: string | null;
};

type CaseDocExecutionItemData = {
  execution_item_id: number;
  row_order: number;
  module_row_id: number | null;
  target_no: number;
  host_name: string;
  excel_cell: string;
  major_no: string | null;
  middle_no: string | null;
  minor_no: string | null;
  tech_doc_text: string | null;
  work_text: string | null;
  check_text: string | null;
  window_text: string | null;
  p_text: string | null;
  command_text: string | null;
  status: CaseDocExecutionStatus;
  performed_at: string | null;
  performed_by: string | null;
  skip_reason: string | null;
  lock_version: number;
  histories: CaseDocExecutionHistoryData[];
};

type CaseDocInstanceListItemData = {
  case_document_id: number;
  case_document_key: string;
  source_doc_id: number;
  source_doc_key: string;
  source_doc_name: string;
  unit_config_id: string;
  status: "active" | "completed";
  total_count: number;
  checked_count: number;
  skipped_count: number;
  pending_count: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

type CaseDocInstanceListData = {
  items: CaseDocInstanceListItemData[];
};

type CaseDocInstanceDetailData = CaseDocInstanceListItemData & {
  prefecture: string;
  building: string;
  targets: CaseDocTargetDeviceSlotData[];
  execution_items: CaseDocExecutionItemData[];
};

type CaseDocSavePickerOptions = {
  suggestedName?: string;
  types?: Array<{
    description?: string;
    accept: Record<string, string[]>;
  }>;
  excludeAcceptAllOption?: boolean;
};

type WindowWithSaveFilePicker = Window & {
  showSaveFilePicker?: (options?: CaseDocSavePickerOptions) => Promise<FileSystemFileHandle>;
};

type CaseDocSaveSelection =
  | { mode: "file-picker"; handle: FileSystemFileHandle }
  | { mode: "browser-download" };

type CaseDocPlaceholderMappingItemData = {
  name: string;
  enabled: boolean;
  scope: "device" | "common";
  source_file: string;
  key_column: string;
  value_column: string;
  source_column: string;
  device_type: string | null;
  key_value: string | null;
  description: string | null;
};

type CaseDocPlaceholderMappingListData = {
  items: CaseDocPlaceholderMappingItemData[];
};

type CaseDocPlaceholderMappingListState = {
  status: "loading" | "available" | "unavailable";
  items: CaseDocPlaceholderMappingItemData[];
  message: string;
};


type CaseDocPlaceholderStatusFilter = "all" | "enabled" | "disabled";

type CaseDocPlaceholderEditorMode = "create" | "edit";

type CaseDocPlaceholderFormState = {
  name: string;
  enabled: boolean;
  scope: "device" | "common";
  device_type: string;
  source_file: string;
  key_column: string;
  value_column: string;
  source_column: string;
  key_value: string;
  description: string;
};

type CaseDocPlaceholderMutationState = {
  status: "idle" | "submitting" | "success" | "error";
  message: string;
};

type ApprovalStatusListItemData = {
  target_id: number;
  target_key: string;
  target_name: string;
  target_type: "source-doc" | "module";
  version_no: number;
  version_major?: number;
  version_minor?: number;
  version_label?: string;
  status: ModuleApiStatus;
  status_label: string;
  next_action: string;
  module_count: number;
  enabled_module_count: number;
  created_by: string | null;
  updated_at: string;
};

type ApprovalStatusListData = {
  items: ApprovalStatusListItemData[];
};

type ApprovalTransitionData = {
  to_status: ModuleApiStatus;
  to_status_label: string;
  action_label: string;
};

type ApprovalStatusHistoryItemData = {
  history_id: number;
  from_status: ModuleApiStatus | null;
  from_status_label: string | null;
  to_status: ModuleApiStatus;
  to_status_label: string;
  action_label: string;
  changed_by: string | null;
  changed_at: string;
  note: string | null;
};

type ApprovalStatusDetailData = {
  target_id: number;
  target_key: string;
  target_name: string;
  target_type: "source-doc" | "module";
  version_no: number;
  version_major?: number;
  version_minor?: number;
  version_label?: string;
  status: ModuleApiStatus;
  status_label: string;
  next_action: string;
  module_count: number;
  enabled_module_count: number;
  module_names: string[];
  description: string | null;
  change_note: string | null;
  created_by: string | null;
  updated_at: string;
  allowed_transitions: ApprovalTransitionData[];
  history: ApprovalStatusHistoryItemData[];
};

type ApprovalStatusListState = {
  status: "loading" | "available" | "unavailable";
  items: ApprovalStatusListItemData[];
  message: string;
};

type ApprovalStatusDetailState = {
  status: "idle" | "loading" | "available" | "unavailable";
  item: ApprovalStatusDetailData | null;
  message: string;
};

type ApprovalStatusMutationState = {
  status: "idle" | "submitting" | "success" | "error";
  message: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const returnReasonRequiredMessage = "差戻し時は理由を入力してください。";

const moduleStatusOptions: { value: "all" | ModuleApiStatus; label: string }[] = [
  { value: "all", label: "すべて" },
  { value: "draft", label: "作成中" },
  { value: "review_requested", label: "承認依頼中" },
  { value: "returned", label: "差戻し" },
  { value: "published", label: "承認済み" },
  { value: "archived", label: "保管済み" },
];

function normalizeModuleFolderPath(folderPath: string): string {
  const normalized = folderPath
    .trim()
    .replace(/\\/g, "/")
    .split("/")
    .map((part) => part.trim())
    .filter((part) => part.length > 0)
    .join("/");
  return normalized || "未分類";
}

function getModuleFolderPaths(item: ModuleListItemData): string[] {
  const folderPaths = item.folder_paths?.length ? item.folder_paths : [item.folder_path || "未分類"];
  return Array.from(new Set(folderPaths.map(normalizeModuleFolderPath)));
}

function ModuleFolderMembershipList({ item }: { item: ModuleListItemData }) {
  return (
    <div className="module-folder-membership-list">
      {getModuleFolderPaths(item).map((folderPath) => (
        <span key={folderPath}>{folderPath}</span>
      ))}
    </div>
  );
}

function buildModuleFolderTreeItems(folders: string[]): ModuleFolderTreeItem[] {
  const directFolders = new Set(folders.map((folder) => normalizeModuleFolderPath(folder)));
  const itemMap = new Map<string, ModuleFolderTreeItem>();

  directFolders.forEach((folder) => {
    const parts = folder.split("/").filter((part) => part.length > 0);
    parts.forEach((part, index) => {
      const path = parts.slice(0, index + 1).join("/");
      const existing = itemMap.get(path);
      itemMap.set(path, {
        path,
        label: part,
        depth: index,
        hasDirectModule: existing?.hasDirectModule === true || directFolders.has(path),
      });
    });
  });

  return Array.from(itemMap.values()).sort((left, right) => left.path.localeCompare(right.path, "ja"));
}

function formatVersionLabel(item: { version_no: number; version_label?: string | null }): string {
  return item.version_label ?? `ver.${item.version_no}.0`;
}

function formatDiffVersionLabel(item: {
  version_no: number;
  version_label?: string | null;
  status_label?: string | null;
}): string {
  const statusLabel = item.status_label ? ` / ${item.status_label}` : "";
  return `${formatVersionLabel(item)}${statusLabel}`;
}

function canRunApprovalTransition(
  role: AuthRole | undefined,
  currentStatus: ModuleApiStatus,
  toStatus: ModuleApiStatus,
): boolean {
  const canRequestReview = (currentStatus === "draft" || currentStatus === "returned") && toStatus === "review_requested";
  const canReview =
    (currentStatus === "review_requested" && (toStatus === "published" || toStatus === "returned"))
    || (currentStatus === "published" && toStatus === "archived");

  if (role === "member") {
    return canRequestReview;
  }

  if (role === "approver" || role === "admin") {
    return canRequestReview || canReview;
  }

  return false;
}

function isReturnTransition(currentStatus: ModuleApiStatus, toStatus: ModuleApiStatus): boolean {
  return currentStatus === "review_requested" && toStatus === "returned";
}

function getLatestReturnHistory(history: ApprovalStatusHistoryItemData[] | undefined): ApprovalStatusHistoryItemData | null {
  return history?.find((item) => item.to_status === "returned") ?? null;
}

function buildApiUrl(path: string): string {
  if (API_BASE_URL) {
    return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
  }

  if (window.location.port === "5173") {
    return `http://localhost:8000${path}`;
  }

  return path;
}

async function selectCaseDocSaveDestination(suggestedName: string): Promise<CaseDocSaveSelection | null> {
  const showSaveFilePicker = (window as WindowWithSaveFilePicker).showSaveFilePicker;
  if (typeof showSaveFilePicker !== "function") {
    return { mode: "browser-download" };
  }

  try {
    const handle = await showSaveFilePicker({
      suggestedName,
      excludeAcceptAllOption: true,
      types: [
        {
          description: "マクロ有効Excelブック",
          accept: {
            "application/vnd.ms-excel.sheet.macroEnabled.12": [".xlsm"],
          },
        },
      ],
    });
    return { mode: "file-picker", handle };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return null;
    }
    throw error;
  }
}

async function saveCaseDocBlob(
  blob: Blob,
  filename: string,
  selection: CaseDocSaveSelection,
): Promise<string> {
  if (selection.mode === "file-picker") {
    const writable = await selection.handle.createWritable();
    try {
      await writable.write(blob);
      await writable.close();
    } catch (error) {
      await writable.abort().catch(() => undefined);
      throw error;
    }
    return selection.handle.name;
  }

  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(downloadUrl);
  return filename;
}

function buildModuleImageUrl(moduleRowImageId: number): string {
  return buildApiUrl(`/api/v1/modules/images/${moduleRowImageId}`);
}

async function readApiResponse<TData>(response: Response): Promise<ApiResponse<TData>> {
  const contentType = response.headers.get("content-type") ?? "";
  const responseText = await response.text();

  if (contentType.includes("application/json")) {
    try {
      const parsed = JSON.parse(responseText) as unknown;
      if (parsed !== null && typeof parsed === "object" && !("result" in parsed) && "detail" in parsed) {
        const detail = (parsed as { detail?: unknown }).detail;
        return {
          result: "error",
          data: null,
          message: typeof detail === "string" ? detail : `API処理に失敗しました。HTTP ${response.status}`,
        };
      }
      return parsed as ApiResponse<TData>;
    } catch {
      return {
        result: "error",
        data: null,
        message: `API応答JSONの解析に失敗しました。HTTP ${response.status}`,
      };
    }
  }

  return {
    result: "error",
    data: null,
    message:
      response.status === 413
        ? "Excelファイルのサイズがアップロード上限を超えています。管理者にアップロード上限の確認を依頼してください。"
        : `APIからJSONではない応答が返りました。HTTP ${response.status}`,
  };
}

const modules: ModuleRow[] = [
  { id: "MOD-001", name: "初期点検手順", category: "点検", owner: "開発担当A", updatedAt: "2026-04-10", status: "Draft", version: "0.2" },
  { id: "MOD-002", name: "部品交換手順", category: "保守", owner: "開発担当B", updatedAt: "2026-04-12", status: "approval", version: "0.3" },
  { id: "MOD-003", name: "復旧確認手順", category: "復旧", owner: "管理者", updatedAt: "2026-04-14", status: "archive", version: "1.0" },
];

const statusLabels: Record<Status, string> = {
  Draft: "作成中",
  approval: "承認待ち",
  archive: "保管済み",
};

function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route element={<Shell />}>
        <Route path="/home" element={<HomePage />} />
        <Route path="/modules/search" element={<ModuleSearchPage />} />
        <Route path="/modules/list" element={<ModuleListPage />} />
        <Route path="/modules/approval" element={<ModuleApprovalStatusPage />} />
        <Route path="/modules/:moduleId" element={<ModuleDetailPage />} />
        <Route path="/modules/register" element={<ModuleRegisterPageV2 />} />
        <Route path="/documents/search" element={<DocumentSearchPage />} />
        <Route path="/documents/create" element={<DocumentEditPage />} />
        <Route path="/documents/:id" element={<DocumentDetailPage />} />
        <Route path="/case-docs" element={<CaseDocsPage />} />
        <Route path="/case-docs/executions" element={<CaseDocExecutionPage />} />
        <Route path="/case-docs/executions/:caseDocumentId" element={<CaseDocExecutionPage />} />
        <Route path="/case-docs/placeholders" element={<CaseDocPlaceholdersPage />} />
        <Route path="/approval" element={<ApprovalPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function Shell() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentUser = getStoredAuthUser();
  const [isLogoutDialogOpen, setIsLogoutDialogOpen] = useState(false);

  useEffect(() => {
    if (currentUser === null) {
      navigate("/", { replace: true });
    }
  }, [currentUser, navigate]);

  if (currentUser === null) {
    return null;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">DB</span>
          <div>
            <strong>手順書DB</strong>
            <small>M1 WebUI</small>
          </div>
        </div>
        <div className="user-box">
          <span>ログイン中</span>
          <strong>{currentUser.displayName}</strong>
          <small>{getAuthRoleLabel(currentUser.role)}</small>
        </div>
        <nav className="sidebar-nav" aria-label="主要メニュー">
          <NavItem to="/home" label="HOME" icon="⌂" />
          <NavGroup label="モジュール">
            <NavItem to="/modules/search" label="一覧" icon="⌕" />
            <NavItem to="/modules/register" label="新規登録" icon="⇧" />
            <NavItem to="/modules/approval" label="承認管理" icon="✓" />
          </NavGroup>
          <NavGroup label="原本">
            <NavItem to="/documents/search" label="一覧" icon="▤" />
            <NavItem to="/documents/create" label="新規作成" icon="✎" />
            <NavItem to="/approval" label="承認管理" icon="✓" />
          </NavGroup>
          <NavGroup label="案件CS">
            <NavItem to="/case-docs" label="新規案件化" icon="CS" end />
            <NavItem to="/case-docs/executions" label="実行・完了" icon="✓" />
          </NavGroup>
          {currentUser.role === "admin" ? (
            <NavGroup label="管理">
              <NavItem to="/case-docs/placeholders" label="プレースホルダ設定" icon="{}" />
            </NavGroup>
          ) : null}
        </nav>
        <div className="flow-box">
          <span>現在の導線</span>
          <strong>{routeTitle(location.pathname)}</strong>
        </div>
        <button
          className="logout-button"
          type="button"
          onClick={() => setIsLogoutDialogOpen(true)}
        >
          <span aria-hidden="true">↩</span>
          ログアウト
        </button>
      </aside>
      <main className="content">
        <WorkflowNavigation pathname={location.pathname} />
        <Outlet />
      </main>
      {isLogoutDialogOpen && (
        <div className="modal-backdrop" role="presentation">
          <section
            aria-labelledby="logout-dialog-title"
            aria-modal="true"
            className="modal-dialog"
            role="dialog"
          >
            <span className="modal-icon" aria-hidden="true">↩</span>
            <h2 id="logout-dialog-title">ログアウトしますか？</h2>
            <p>現在の画面を終了し、ログイン画面へ戻ります。</p>
            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setIsLogoutDialogOpen(false)}>
                キャンセル
              </button>
              <button
                className="danger"
                type="button"
                onClick={() => {
                  setIsLogoutDialogOpen(false);
                  clearAuthUser();
                  window.localStorage.removeItem("approvalActor");
                  navigate("/", { replace: true });
                }}
              >
                <span aria-hidden="true">↩</span>
                ログアウト
              </button>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function NavItem({ to, label, icon, end = false }: { to: string; label: string; icon: string; end?: boolean }) {
  return (
    <NavLink to={to} end={end} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
      <span aria-hidden="true">{icon}</span>
      {label}
    </NavLink>
  );
}

function NavGroup({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="sidebar-nav-group" aria-label={label}>
      <h2>{label}</h2>
      <div className="sidebar-nav-links">{children}</div>
    </section>
  );
}

const workflowStages = [
  { label: "モジュール", to: "/modules/search" },
  { label: "原本", to: "/documents/search" },
  { label: "案件化", to: "/case-docs" },
  { label: "実行", to: "/case-docs/executions" },
];

function workflowStageIndex(pathname: string): number {
  if (pathname.startsWith("/modules/")) return 0;
  if (pathname.startsWith("/documents/") || pathname === "/approval") return 1;
  if (pathname.startsWith("/case-docs/executions")) return 3;
  if (pathname === "/case-docs") return 2;
  return -1;
}

function WorkflowNavigation({ pathname }: { pathname: string }) {
  const activeIndex = workflowStageIndex(pathname);

  return (
    <nav className="workflow-navigation" aria-label="業務工程">
      {workflowStages.map((stage, index) => (
        <Fragment key={stage.to}>
          {index > 0 ? <span className="workflow-navigation-arrow" aria-hidden="true">→</span> : null}
          <NavLink
            to={stage.to}
            className={`workflow-navigation-step${index === activeIndex ? " active" : ""}${activeIndex > index ? " passed" : ""}`}
          >
            <span>{index + 1}</span>
            {stage.label}
          </NavLink>
        </Fragment>
      ))}
    </nav>
  );
}

function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("member");
  const [password, setPassword] = useState("password");
  const [loginError, setLoginError] = useState("");

  function handleLogin(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const normalizedUsername = username.trim();
    const demoUser = demoUsers[normalizedUsername];

    if (demoUser === undefined || demoUser.password !== password) {
      setLoginError("ユーザー名またはパスワードが正しくありません。");
      return;
    }

    const authUser: AuthUser = {
      username: demoUser.username,
      displayName: demoUser.displayName,
      role: demoUser.role,
    };
    saveAuthUser(authUser);
    window.localStorage.setItem("approvalActor", authUser.displayName);
    setLoginError("");
    navigate("/home");
  }

  return (
    <main className="login-screen">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-copy">
          <p className="eyebrow">Sprint 1 / SB1-04</p>
          <h1 id="login-title">手順書DB WebUI</h1>
          <p>モジュール登録、検索、原本作成、原本承認状態確認までの主要操作をWebUIから辿れるM1向け画面です。</p>
          <div className="demo-users">
            <span>テストユーザー</span>
            <strong>member / password</strong>
            <small>参照・作成・編集用</small>
            <strong>approver / password</strong>
            <small>承認・差戻し・保管用</small>
          </div>
        </div>
        <form className="login-form" onSubmit={handleLogin}>
          <label>
            ユーザ名
            <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
          </label>
          <label>
            パスワード
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>
          {loginError ? <p className="login-error">{loginError}</p> : null}
          <button className="primary" type="submit">
            <span aria-hidden="true">→</span>
            ログイン
          </button>
        </form>
      </section>
    </main>
  );
}

type ModuleImagePlacement = "work" | "expected";

function getExcelColumnIndex(cellAddress: string): number | null {
  const columnLetters = cellAddress.match(/^[A-Za-z]+/)?.[0];
  if (!columnLetters) {
    return null;
  }

  return columnLetters
    .toUpperCase()
    .split("")
    .reduce((total, character) => total * 26 + character.charCodeAt(0) - 64, 0);
}

function getModuleImagePlacement(image: ModuleRowImageData): ModuleImagePlacement {
  const columnIndex = getExcelColumnIndex(image.anchor_cell);
  return columnIndex !== null && columnIndex >= 9 ? "expected" : "work";
}

function ModuleRowImageList({
  images,
  placement,
}: {
  images: ModuleRowImageData[];
  placement: ModuleImagePlacement;
}) {
  const placementImages = images.filter((image) => getModuleImagePlacement(image) === placement);
  if (placementImages.length === 0) {
    return null;
  }

  return (
    <div className="excel-image-list">
      {placementImages.map((image) => {
        const imageId = image.module_row_image_id;
        const key = imageId ?? image.image_key;
        return (
          <figure key={`${key}-${image.anchor_cell}`} className="excel-image-card">
            {typeof imageId === "number" ? (
              <img
                src={buildModuleImageUrl(imageId)}
                alt={`${image.image_key} ${image.anchor_cell}`}
                loading="lazy"
              />
            ) : (
              <div className="excel-image-placeholder">登録後に画像を表示できます</div>
            )}
            <figcaption>{image.anchor_cell}</figcaption>
          </figure>
        );
      })}
    </div>
  );
}

type HomeOverviewState = {
  status: "loading" | "available" | "unavailable";
  modulesPublished: number;
  sourceDocsPublished: number;
  activeCaseDocs: number;
  completedCaseDocs: number;
  modulesNeedAction: number;
  sourceDocsNeedAction: number;
  message: string;
};

function HomePage() {
  const currentUser = getStoredAuthUser();
  const [overview, setOverview] = useState<HomeOverviewState>({
    status: "loading",
    modulesPublished: 0,
    sourceDocsPublished: 0,
    activeCaseDocs: 0,
    completedCaseDocs: 0,
    modulesNeedAction: 0,
    sourceDocsNeedAction: 0,
    message: "作業状況を取得しています。",
  });

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchOverview(): Promise<void> {
      try {
        const [modulesResponse, sourceDocsResponse, caseDocsResponse] = await Promise.all([
          fetch(buildApiUrl("/api/v1/modules"), { signal: abortController.signal }),
          fetch(buildApiUrl("/api/v1/source-docs"), { signal: abortController.signal }),
          fetch(buildApiUrl("/api/v1/case-docs/instances"), { signal: abortController.signal }),
        ]);
        const [modulesBody, sourceDocsBody, caseDocsBody] = await Promise.all([
          readApiResponse<ModuleListData>(modulesResponse),
          readApiResponse<SourceDocListData>(sourceDocsResponse),
          readApiResponse<CaseDocInstanceListData>(caseDocsResponse),
        ]);

        if (
          !modulesResponse.ok || modulesBody.result !== "success" || modulesBody.data === null
          || !sourceDocsResponse.ok || sourceDocsBody.result !== "success" || sourceDocsBody.data === null
          || !caseDocsResponse.ok || caseDocsBody.result !== "success" || caseDocsBody.data === null
        ) {
          setOverview((current) => ({ ...current, status: "unavailable", message: "作業状況の一部を取得できませんでした。" }));
          return;
        }

        const actionStatuses: ModuleApiStatus[] =
          currentUser?.role === "member"
            ? ["draft", "returned"]
            : ["draft", "returned", "review_requested"];
        setOverview({
          status: "available",
          modulesPublished: modulesBody.data.items.filter((item) => item.status === "published").length,
          sourceDocsPublished: sourceDocsBody.data.items.filter((item) => item.status === "published").length,
          activeCaseDocs: caseDocsBody.data.items.filter((item) => item.status === "active").length,
          completedCaseDocs: caseDocsBody.data.items.filter((item) => item.status === "completed").length,
          modulesNeedAction: modulesBody.data.items.filter((item) => actionStatuses.includes(item.status)).length,
          sourceDocsNeedAction: sourceDocsBody.data.items.filter((item) => actionStatuses.includes(item.status)).length,
          message: "最新の作業状況を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setOverview((current) => ({ ...current, status: "unavailable", message: "作業状況の取得中にAPI接続で失敗しました。" }));
      }
    }

    void fetchOverview();
    return () => abortController.abort();
  }, [currentUser?.role]);

  const approvalRoute = currentUser?.role === "member" ? "/modules/search" : "/modules/approval";
  const sourceApprovalRoute = currentUser?.role === "member" ? "/documents/search" : "/approval";

  return (
    <Page title="HOME" description="モジュールから原本、案件CSの実行まで、現在の進捗と次の作業を確認します。">
      <section className="workflow-dashboard" aria-label="業務工程の状況">
        <WorkflowStageCard step="1" title="モジュール" count={overview.modulesPublished} unit="件承認済み" to="/modules/search" action="一覧を開く" />
        <WorkflowStageCard step="2" title="原本" count={overview.sourceDocsPublished} unit="件承認済み" to="/documents/search" action="一覧を開く" />
        <WorkflowStageCard step="3" title="案件化" count={overview.activeCaseDocs} unit="件実行待ち" to="/case-docs" action="案件化する" />
        <WorkflowStageCard step="4" title="実行" count={overview.completedCaseDocs} unit="件完了" to="/case-docs/executions" action="実行画面を開く" />
      </section>

      <section className="section-band work-queue-section">
        <div className="section-heading-row">
          <div>
            <h2>対応が必要な作業</h2>
            <p>{overview.message}</p>
          </div>
          <span className={`overview-state overview-state-${overview.status}`}>
            {overview.status === "loading" ? "取得中" : overview.status === "available" ? "最新" : "取得失敗"}
          </span>
        </div>
        <div className="work-queue-grid">
          <WorkQueueCard title="モジュール" count={overview.modulesNeedAction} to={approvalRoute} action="確認する" />
          <WorkQueueCard title="原本" count={overview.sourceDocsNeedAction} to={sourceApprovalRoute} action="確認する" />
          <WorkQueueCard title="案件CS" count={overview.activeCaseDocs} to="/case-docs/executions" action="続きから実行" />
        </div>
      </section>

      <ApiHealthPanel />
    </Page>
  );
}

function ApiHealthPanel() {
  const [apiHealthState, setApiHealthState] = useState<HealthCheckState>({
    status: "checking",
    primary: "-",
    secondary: "-",
    message: "API疎通を確認中です。",
  });
  const [databaseHealthState, setDatabaseHealthState] = useState<HealthCheckState>({
    status: "checking",
    primary: "-",
    secondary: "-",
    message: "DB疎通を確認中です。",
  });

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchHealth(): Promise<void> {
      try {
        const response = await fetch(buildApiUrl("/api/v1/health"), {
          signal: abortController.signal,
        });

        if (!response.ok) {
          setApiHealthState({
            status: "unavailable",
            primary: "-",
            secondary: "-",
            message: `API応答エラー: HTTP ${response.status}`,
          });
          return;
        }

        const responseBody = (await response.json()) as ApiResponse<HealthData>;
        if (responseBody.result !== "success" || responseBody.data === null) {
          setApiHealthState({
            status: "unavailable",
            primary: "-",
            secondary: "-",
            message: responseBody.message || "API疎通確認に失敗しました。",
          });
          return;
        }

        setApiHealthState({
          status: "available",
          primary: responseBody.data.service,
          secondary: responseBody.data.environment,
          message: responseBody.message,
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setApiHealthState({
          status: "unavailable",
          primary: "-",
          secondary: "-",
          message: "APIに接続できません。",
        });
      }
    }

    async function fetchDatabaseHealth(): Promise<void> {
      try {
        const response = await fetch(buildApiUrl("/api/v1/health/db"), {
          signal: abortController.signal,
        });

        if (!response.ok) {
          setDatabaseHealthState({
            status: "unavailable",
            primary: "-",
            secondary: "-",
            message: `DB応答エラー: HTTP ${response.status}`,
          });
          return;
        }

        const responseBody = (await response.json()) as ApiResponse<DatabaseHealthData>;
        if (responseBody.result !== "success" || responseBody.data === null) {
          setDatabaseHealthState({
            status: "unavailable",
            primary: "-",
            secondary: "-",
            message: responseBody.message || "DB疎通確認に失敗しました。",
          });
          return;
        }

        setDatabaseHealthState({
          status: "available",
          primary: responseBody.data.database,
          secondary: `${responseBody.data.host}:${responseBody.data.port}`,
          message: responseBody.message,
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setDatabaseHealthState({
          status: "unavailable",
          primary: "-",
          secondary: "-",
          message: "DB疎通APIに接続できません。",
        });
      }
    }

    void fetchHealth();
    void fetchDatabaseHealth();

    return () => {
      abortController.abort();
    };
  }, []);

  const labelMap: Record<HealthCheckState["status"], string> = {
    checking: "確認中",
    available: "接続OK",
    unavailable: "未接続",
  };

  return (
    <section className="api-health" aria-label="APIとDBの疎通状態">
      <HealthStatusRow
        label="API疎通"
        state={apiHealthState}
        statusLabel={labelMap[apiHealthState.status]}
        primaryLabel="サービス"
        secondaryLabel="環境"
      />
      <HealthStatusRow
        label="DB疎通"
        state={databaseHealthState}
        statusLabel={labelMap[databaseHealthState.status]}
        primaryLabel="DB"
        secondaryLabel="接続先"
      />
    </section>
  );
}

function HealthStatusRow({
  label,
  state,
  statusLabel,
  primaryLabel,
  secondaryLabel,
}: {
  label: string;
  state: HealthCheckState;
  statusLabel: string;
  primaryLabel: string;
  secondaryLabel: string;
}) {
  return (
    <div className="health-row">
      <div className={`api-health-indicator ${state.status}`} aria-hidden="true" />
      <div>
        <span>{label}</span>
        <strong>{statusLabel}</strong>
      </div>
      <div>
        <span>{primaryLabel}</span>
        <strong>{state.primary}</strong>
      </div>
      <div>
        <span>{secondaryLabel}</span>
        <strong>{state.secondary}</strong>
      </div>
      <p>{state.message}</p>
    </div>
  );
}

function ModuleSearchPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialKeyword = searchParams.get("keyword") ?? "";
  const initialStatus = (searchParams.get("status") ?? "all") as (typeof moduleStatusOptions)[number]["value"];
  const initialCreatedBy = searchParams.get("created_by") ?? "";
  const initialFolderPaths = Array.from(
    new Set(
      searchParams
        .getAll("folder_path")
        .map(normalizeModuleFolderPath)
        .filter((folderPath) => folderPath.length > 0),
    ),
  );
  const initialFolderPathKey = initialFolderPaths.join("\u001f");
  const initialFolderPath = initialFolderPaths[0] ?? "";
  const initialUpdatedFrom = searchParams.get("updated_from") ?? "";
  const initialUpdatedTo = searchParams.get("updated_to") ?? "";
  const initialSort = searchParams.get("sort") ?? "key_asc";
  const [keywordInput, setKeywordInput] = useState(initialKeyword);
  const [statusInput, setStatusInput] = useState(initialStatus);
  const [createdByInput, setCreatedByInput] = useState(initialCreatedBy);
  const [folderPathInputs, setFolderPathInputs] = useState<string[]>(initialFolderPaths);
  const [updatedFromInput, setUpdatedFromInput] = useState(initialUpdatedFrom);
  const [updatedToInput, setUpdatedToInput] = useState(initialUpdatedTo);
  const [sortInput, setSortInput] = useState(initialSort);
  const keyword = initialKeyword;
  const statusFilter = initialStatus;
  const createdByFilter = initialCreatedBy;
  const folderPathFilters = initialFolderPaths;
  const folderPathFilter = folderPathFilters[0] ?? "";
  const updatedFromFilter = initialUpdatedFrom;
  const updatedToFilter = initialUpdatedTo;
  const sortFilter = initialSort;
  const [moduleListState, setModuleListState] = useState<ModuleListState>({
    status: "loading",
    items: [],
    folders: [],
    message: "モジュール一覧を取得しています。",
  });
  const [folderRenameInput, setFolderRenameInput] = useState(initialFolderPath || "未分類");
  const [folderRenameState, setFolderRenameState] = useState<ModuleFolderRenameState>({
    status: "idle",
    message: "操作対象のタグ名を変更できます。",
  });
  const [folderDeleteState, setFolderDeleteState] = useState<ModuleFolderRenameState>({
    status: "idle",
    message: "操作対象のタグを削除できます。",
  });
  const [isFolderDeleteConfirmOpen, setIsFolderDeleteConfirmOpen] = useState(false);
  const [selectedModuleIds, setSelectedModuleIds] = useState<number[]>([]);
  const [isFolderCreateOpen, setIsFolderCreateOpen] = useState(false);
  const [folderCreateInput, setFolderCreateInput] = useState("");
  const [folderCreateState, setFolderCreateState] = useState<ModuleFolderMoveState>({
    status: "idle",
    message: "新規タグには最低1つのモジュールを関連付けます。",
  });
  const [folderMoveTarget, setFolderMoveTarget] = useState(initialFolderPath || "未分類");
  const [folderMoveState, setFolderMoveState] = useState<ModuleFolderMoveState>({
    status: "idle",
    message: "既存タグを残したまま追加します。未分類を選ぶと他のタグを解除します。",
  });

  useEffect(() => {
    setKeywordInput(initialKeyword);
    setStatusInput(initialStatus);
    setCreatedByInput(initialCreatedBy);
    setFolderPathInputs(initialFolderPaths);
    setFolderRenameInput(initialFolderPath || "未分類");
    setFolderMoveTarget(initialFolderPath || "未分類");
    setFolderRenameState({ status: "idle", message: "操作対象のタグ名を変更できます。" });
    setFolderDeleteState({ status: "idle", message: "操作対象のタグを削除できます。" });
    setIsFolderDeleteConfirmOpen(false);
    setFolderCreateState({ status: "idle", message: "新規タグには最低1つのモジュールを関連付けます。" });
    setFolderMoveState({ status: "idle", message: "選択したモジュールに既存タグを追加できます。" });
    setUpdatedFromInput(initialUpdatedFrom);
    setUpdatedToInput(initialUpdatedTo);
    setSortInput(initialSort);
  }, [initialKeyword, initialStatus, initialCreatedBy, initialFolderPathKey, initialUpdatedFrom, initialUpdatedTo, initialSort]);

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchModules(): Promise<void> {
      setModuleListState({
        status: "loading",
        items: [],
        folders: [],
        message: "モジュール一覧を取得しています。",
      });

      try {
        const endpoint = new URL(buildApiUrl("/api/v1/modules"), window.location.origin);

        if (keyword) endpoint.searchParams.set("keyword", keyword);
        if (statusFilter !== "all") endpoint.searchParams.set("status", statusFilter);
        if (createdByFilter) endpoint.searchParams.set("created_by", createdByFilter);
        folderPathFilters.forEach((folderPath) => endpoint.searchParams.append("folder_path", folderPath));
        if (updatedFromFilter) endpoint.searchParams.set("updated_from", updatedFromFilter);
        if (updatedToFilter) endpoint.searchParams.set("updated_to", updatedToFilter);
        if (sortFilter !== "key_asc") endpoint.searchParams.set("sort", sortFilter);

        const response = await fetch(endpoint.toString(), { signal: abortController.signal });
        const responseBody = (await response.json()) as ApiResponse<ModuleListData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setModuleListState({
            status: "unavailable",
            items: [],
            folders: [],
            message: responseBody.message || "モジュール一覧の取得に失敗しました。HTTP " + response.status,
          });
          return;
        }

        setModuleListState({
          status: "available",
          items: responseBody.data.items,
          folders: responseBody.data.folders ?? [],
          message: responseBody.message || "モジュール一覧を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setModuleListState({ status: "unavailable", items: [], folders: [], message: "APIに接続できませんでした。" });
      }
    }

    void fetchModules();

    return () => abortController.abort();
  }, [keyword, statusFilter, createdByFilter, initialFolderPathKey, updatedFromFilter, updatedToFilter, sortFilter]);

  useEffect(() => {
    setSelectedModuleIds((current) =>
      current.filter((moduleId) => moduleListState.items.some((item) => item.module_id === moduleId)),
    );
  }, [moduleListState.items]);

  function navigateWithFilters(filters: {
    keyword: string;
    status: (typeof moduleStatusOptions)[number]["value"];
    createdBy: string;
    folderPaths: string[];
    updatedFrom: string;
    updatedTo: string;
    sort: string;
  }): void {
    const params = new URLSearchParams();
    const normalizedKeyword = filters.keyword.trim();
    const normalizedCreatedBy = filters.createdBy.trim();
    const normalizedFolderPaths = Array.from(
      new Set(
        filters.folderPaths
          .map(normalizeModuleFolderPath)
          .filter((folderPath) => folderPath.length > 0),
      ),
    );

    if (normalizedKeyword) params.set("keyword", normalizedKeyword);
    if (filters.status !== "all") params.set("status", filters.status);
    if (normalizedCreatedBy) params.set("created_by", normalizedCreatedBy);
    normalizedFolderPaths.forEach((folderPath) => params.append("folder_path", folderPath));
    if (filters.updatedFrom) params.set("updated_from", filters.updatedFrom);
    if (filters.updatedTo) params.set("updated_to", filters.updatedTo);
    if (filters.sort !== "key_asc") params.set("sort", filters.sort);

    const query = params.toString();
    navigate(query ? "/modules/search?" + query : "/modules/search");
  }

  function handleSubmit(): void {
    navigateWithFilters({
      keyword: keywordInput,
      status: statusInput,
      createdBy: createdByInput,
      folderPaths: folderPathInputs,
      updatedFrom: updatedFromInput,
      updatedTo: updatedToInput,
      sort: sortInput,
    });
  }

  function handleStatusFilterChange(nextStatus: (typeof moduleStatusOptions)[number]["value"]): void {
    setStatusInput(nextStatus);
    navigateWithFilters({
      keyword,
      status: nextStatus,
      createdBy: createdByFilter,
      folderPaths: folderPathFilters,
      updatedFrom: updatedFromFilter,
      updatedTo: updatedToFilter,
      sort: sortFilter,
    });
  }

  function handleTagFilterToggle(nextFolderPath: string): void {
    const normalizedFolderPath = normalizeModuleFolderPath(nextFolderPath);
    const nextFolderPaths = folderPathFilters.includes(normalizedFolderPath)
      ? folderPathFilters.filter((folderPath) => folderPath !== normalizedFolderPath)
      : [normalizedFolderPath, ...folderPathFilters];
    setFolderPathInputs(nextFolderPaths);
    navigateWithFilters({
      keyword,
      status: statusFilter,
      createdBy: createdByFilter,
      folderPaths: nextFolderPaths,
      updatedFrom: updatedFromFilter,
      updatedTo: updatedToFilter,
      sort: sortFilter,
    });
  }

  function handleTagFilterClear(): void {
    setFolderPathInputs([]);
    navigateWithFilters({
      keyword,
      status: statusFilter,
      createdBy: createdByFilter,
      folderPaths: [],
      updatedFrom: updatedFromFilter,
      updatedTo: updatedToFilter,
      sort: sortFilter,
    });
  }

  function toggleTagInput(nextFolderPath: string): void {
    const normalizedFolderPath = normalizeModuleFolderPath(nextFolderPath);
    setFolderPathInputs((current) =>
      current.includes(normalizedFolderPath)
        ? current.filter((folderPath) => folderPath !== normalizedFolderPath)
        : [...current, normalizedFolderPath],
    );
  }

  async function handleFolderRenameSubmit(): Promise<void> {
    const currentFolder = normalizeModuleFolderPath(folderPathFilter || "未分類");
    const nextFolder = normalizeModuleFolderPath(folderRenameInput);

    if (folderPathFilter === "") {
      setFolderRenameState({ status: "error", message: "先に変更対象のタグを選択してください。" });
      return;
    }

    if (currentFolder === nextFolder) {
      setFolderRenameState({ status: "error", message: "変更前と変更後のタグ名が同じです。" });
      return;
    }

    setFolderRenameState({ status: "submitting", message: "タグ名を変更しています。" });

    try {
      const response = await fetch(buildApiUrl("/api/v1/modules/folders"), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_folder_path: currentFolder, new_folder_path: nextFolder }),
      });
      const responseBody = await readApiResponse<ModuleListData>(response);

      if (!response.ok || responseBody.result !== "success") {
        setFolderRenameState({
          status: "error",
          message: responseBody.message || `タグ名の変更に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setFolderRenameState({ status: "success", message: responseBody.message || "タグ名を変更しました。" });
      const nextFolderPaths = [
        nextFolder,
        ...folderPathFilters.filter((folderPath) => folderPath !== currentFolder && folderPath !== nextFolder),
      ];
      setFolderPathInputs(nextFolderPaths);
      navigateWithFilters({
        keyword,
        status: statusFilter,
        createdBy: createdByFilter,
        folderPaths: nextFolderPaths,
        updatedFrom: updatedFromFilter,
        updatedTo: updatedToFilter,
        sort: sortFilter,
      });
    } catch (error) {
      setFolderRenameState({ status: "error", message: "タグ名の変更中にAPI接続で失敗しました。" });
    }
  }

  async function handleFolderDeleteConfirm(): Promise<void> {
    const targetFolder = normalizeModuleFolderPath(folderPathFilter);
    setFolderDeleteState({ status: "submitting", message: "タグを削除しています。" });

    try {
      const response = await fetch(buildApiUrl("/api/v1/modules/folders"), {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder_path: targetFolder }),
      });
      const responseBody = await readApiResponse<ModuleListData>(response);

      if (!response.ok || responseBody.result !== "success") {
        setFolderDeleteState({
          status: "error",
          message: responseBody.message || `タグの削除に失敗しました。HTTP ${response.status}`,
        });
        setIsFolderDeleteConfirmOpen(false);
        return;
      }

      setIsFolderDeleteConfirmOpen(false);
      setFolderDeleteState({ status: "success", message: responseBody.message || "タグを削除しました。" });
      const nextFolderPaths = folderPathFilters.filter((folderPath) => folderPath !== targetFolder);
      setFolderPathInputs(nextFolderPaths);
      navigateWithFilters({
        keyword,
        status: statusFilter,
        createdBy: createdByFilter,
        folderPaths: nextFolderPaths,
        updatedFrom: updatedFromFilter,
        updatedTo: updatedToFilter,
        sort: sortFilter,
      });
    } catch (error) {
      setFolderDeleteState({ status: "error", message: "タグ削除中にAPI接続で失敗しました。" });
      setIsFolderDeleteConfirmOpen(false);
    }
  }

  function toggleSelectedModule(moduleId: number): void {
    setSelectedModuleIds((current) =>
      current.includes(moduleId) ? current.filter((selectedId) => selectedId !== moduleId) : [...current, moduleId],
    );
  }

  function toggleAllVisibleModules(): void {
    const visibleModuleIds = Array.from(new Set(moduleListState.items.map((item) => item.module_id)));
    const allVisibleSelected = visibleModuleIds.length > 0 && visibleModuleIds.every((moduleId) => selectedModuleIds.includes(moduleId));
    setSelectedModuleIds(allVisibleSelected ? [] : visibleModuleIds);
  }

  async function moveSelectedModulesToFolder(targetFolder: string): Promise<ApiResponse<ModuleListData>> {
    const response = await fetch(buildApiUrl("/api/v1/modules/folders/modules"), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ module_ids: selectedModuleIds, folder_path: targetFolder }),
    });
    return readApiResponse<ModuleListData>(response);
  }

  async function handleFolderCreateSubmit(): Promise<void> {
    const targetFolder = normalizeModuleFolderPath(folderCreateInput);

    if (selectedModuleIds.length === 0) {
      setFolderCreateState({ status: "error", message: "最低1つのモジュールを選択してください。" });
      return;
    }

    if (folderOptions.some((folder) => normalizeModuleFolderPath(folder) === targetFolder)) {
      setFolderCreateState({ status: "error", message: "同じ名前のタグが既にあります。既存タグへの追加を使ってください。" });
      return;
    }

    setFolderCreateState({ status: "submitting", message: "タグを作成し、選択モジュールへ関連付けています。" });

    try {
      const responseBody = await moveSelectedModulesToFolder(targetFolder);

      if (responseBody.result !== "success") {
        setFolderCreateState({ status: "error", message: responseBody.message || "タグ追加に失敗しました。" });
        return;
      }

      setSelectedModuleIds([]);
      setFolderCreateInput("");
      setIsFolderCreateOpen(false);
      setFolderCreateState({ status: "success", message: responseBody.message || "タグを追加しました。" });
      navigateWithFilters({
        keyword,
        status: statusFilter,
        createdBy: createdByFilter,
        folderPaths: [targetFolder],
        updatedFrom: updatedFromFilter,
        updatedTo: updatedToFilter,
        sort: sortFilter,
      });
    } catch (error) {
      setFolderCreateState({ status: "error", message: "タグ追加中にAPI接続で失敗しました。" });
    }
  }

  function handleFolderCreateCancel(): void {
    setIsFolderCreateOpen(false);
    setFolderCreateInput("");
    setFolderCreateState({ status: "idle", message: "新規タグには最低1つのモジュールを関連付けます。" });
  }

  async function handleFolderMoveSubmit(): Promise<void> {
    const targetFolder = normalizeModuleFolderPath(folderMoveTarget);

    if (selectedModuleIds.length === 0) {
      setFolderMoveState({ status: "error", message: "タグを追加するモジュールを選択してください。" });
      return;
    }

    setFolderMoveState({ status: "submitting", message: "選択したモジュールへタグを追加しています。" });

    try {
      const responseBody = await moveSelectedModulesToFolder(targetFolder);

      if (responseBody.result !== "success") {
        setFolderMoveState({ status: "error", message: responseBody.message || "タグの追加に失敗しました。" });
        return;
      }

      setSelectedModuleIds([]);
      setFolderMoveState({ status: "success", message: responseBody.message || "選択したモジュールへタグを追加しました。" });
      navigateWithFilters({
        keyword,
        status: statusFilter,
        createdBy: createdByFilter,
        folderPaths: [targetFolder],
        updatedFrom: updatedFromFilter,
        updatedTo: updatedToFilter,
        sort: sortFilter,
      });
    } catch (error) {
      setFolderMoveState({ status: "error", message: "タグ追加中にAPI接続で失敗しました。" });
    }
  }

  const statusFilterLabel = moduleStatusOptions.find((option) => option.value === statusFilter)?.label ?? statusFilter;
  const moduleFolderOptions = moduleListState.folders ?? [];
  const folderOptions = moduleFolderOptions.length > 0 ? moduleFolderOptions : ["未分類"];
  const folderTreeItems = buildModuleFolderTreeItems(folderOptions);
  const selectedTagFilterLabel = folderPathFilters.length > 0 ? folderPathFilters.join("、") : "すべて";
  const selectedFolderLabel = folderPathFilter || "未選択";
  const canRenameFolder = folderPathFilter !== "" && folderRenameState.status !== "submitting";
  const canDeleteFolder = folderPathFilter !== "" && folderPathFilter !== "未分類" && folderDeleteState.status !== "submitting";
  const visibleModuleIds = Array.from(new Set(moduleListState.items.map((item) => item.module_id)));
  const allVisibleModulesSelected = visibleModuleIds.length > 0 && visibleModuleIds.every((moduleId) => selectedModuleIds.includes(moduleId));
  const canCreateFolder = folderCreateState.status !== "submitting";
  const canMoveSelectedModules = selectedModuleIds.length > 0 && folderMoveState.status !== "submitting";

  return (
    <Page title={"モジュール検索"} description={"APIから取得したモジュール一覧を検索し、詳細情報と版管理を確認できます。"}>
      <form className="search-form module-search-form" onSubmit={(event) => { event.preventDefault(); handleSubmit(); }}>
        <label>
          {"キーワード"}
          <input placeholder="MOD-001 / 点検 / TeraTerm" value={keywordInput} onChange={(event) => setKeywordInput(event.target.value)} />
        </label>
        <label>
          {"承認状態"}
          <select value={statusInput} onChange={(event) => setStatusInput(event.target.value as (typeof moduleStatusOptions)[number]["value"])}>
            {moduleStatusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label>
          {"作成者"}
          <input placeholder="seed / webui" value={createdByInput} onChange={(event) => setCreatedByInput(event.target.value)} />
        </label>
        <fieldset className="module-tag-filter-field">
          <legend>タグ</legend>
          <details className="module-tag-filter-select">
            <summary>
              <span>{folderPathInputs.length > 0 ? `${folderPathInputs.length}件選択` : "すべて"}</span>
              <small>{folderPathInputs.length > 0 ? folderPathInputs.join("、") : "タグを選択"}</small>
            </summary>
            <div className="module-tag-filter-menu">
              <div className="module-tag-filter-options">
                {folderOptions.map((folder) => (
                  <label key={folder}>
                    <input
                      type="checkbox"
                      checked={folderPathInputs.includes(folder)}
                      onChange={() => toggleTagInput(folder)}
                    />
                    <span>{folder}</span>
                  </label>
                ))}
              </div>
              <div className="module-tag-filter-footer">
                <small>複数選択時は、すべてのタグを持つモジュールを表示します。</small>
                <button className="text-button" type="button" onClick={() => setFolderPathInputs([])}>
                  選択解除
                </button>
              </div>
            </div>
          </details>
        </fieldset>
        <label>
          {"更新日"}
          <input
            type="date"
            value={updatedFromInput}
            onChange={(event) => {
              setUpdatedFromInput(event.target.value);
              setUpdatedToInput(event.target.value);
            }}
          />
        </label>
        <label>
          {"並び替え"}
          <select value={sortInput} onChange={(event) => setSortInput(event.target.value)}>
            <option value="key_asc">{"ID昇順"}</option>
            <option value="key_desc">{"ID降順"}</option>
            <option value="updated_desc">{"更新日が新しい順"}</option>
            <option value="updated_asc">{"更新日が古い順"}</option>
            <option value="status_asc">{"承認状態順"}</option>
          </select>
        </label>
        <button className="primary" type="submit"><span aria-hidden="true">⌕</span>{"検索"}</button>
      </form>

      <section className={"list-status list-status-" + moduleListState.status} aria-live="polite">
        <div><span>{"取得状態"}</span><strong>{moduleListState.status === "loading" ? "取得中" : moduleListState.status === "available" ? "取得完了" : "取得失敗"}</strong></div>
        <div><span>{"検索キーワード"}</span><strong>{keyword || "指定なし"}</strong></div>
        <div><span>{"承認状態"}</span><strong>{statusFilterLabel}</strong></div>
        <div><span>{"作成者"}</span><strong>{createdByFilter || "指定なし"}</strong></div>
        <div><span>タグ</span><strong>{selectedTagFilterLabel}</strong></div>
        <p>{moduleListState.message}</p>
      </section>

      <div className="module-explorer-layout">
        <aside className="module-folder-pane" aria-label="モジュールタグ">
          <div className="module-folder-pane-header">
            <span>タグ</span>
            <strong>{selectedTagFilterLabel}</strong>
          </div>
          <button
            type="button"
            className={folderPathFilters.length === 0 ? "module-folder-button active" : "module-folder-button"}
            onClick={handleTagFilterClear}
          >
            <span aria-hidden="true">▦</span>
            <span>すべて</span>
          </button>
          <div className="module-folder-tree" role="tree" aria-label="タグ一覧">
            {folderTreeItems.map((folder) => (
              <button
                key={folder.path}
                type="button"
                role="treeitem"
                aria-level={folder.depth + 1}
                aria-pressed={folderPathFilters.includes(folder.path)}
                className={folderPathFilters.includes(folder.path) ? "module-folder-button active" : "module-folder-button"}
                style={{ "--folder-depth": folder.depth } as CSSProperties}
                onClick={() => handleTagFilterToggle(folder.path)}
              >
                <span aria-hidden="true">{folderPathFilters.includes(folder.path) ? "✓" : folder.hasDirectModule ? "◇" : "▸"}</span>
                <span>{folder.label}</span>
              </button>
            ))}
          </div>
          <div className="module-folder-delete-panel">
            <button
              type="button"
              className="danger"
              disabled={!canDeleteFolder}
              onClick={() => setIsFolderDeleteConfirmOpen(true)}
            >
              タグを削除
            </button>
            <p className={"module-folder-action-message " + folderDeleteState.status}>
              {folderPathFilter === "未分類" ? "未分類タグは削除できません。" : folderDeleteState.message}
            </p>
          </div>
        </aside>

        <div className="module-explorer-main">
          <section className="approval-flow" aria-label="モジュール承認状態フィルター">
            {moduleStatusOptions.map((option) => (
              <button key={option.value} type="button" className={option.value === statusFilter ? "approval-filter-button active" : "approval-filter-button"} onClick={() => handleStatusFilterChange(option.value)}>{option.label}</button>
            ))}
          </section>

          <section className="module-folder-action-panel" aria-label="モジュールタグ操作">
            <div className="module-folder-action-summary">
              <span>選択中</span>
              <strong>{selectedModuleIds.length} 件</strong>
            </div>

            <div className="module-folder-action-card">
              <header>
                <h2>タグ新規追加</h2>
                {!isFolderCreateOpen ? (
                  <button className="secondary" type="button" onClick={() => setIsFolderCreateOpen(true)}>
                    + 追加
                  </button>
                ) : null}
              </header>
              {isFolderCreateOpen ? (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void handleFolderCreateSubmit();
                  }}
                >
                  <label>
                    新規タグ名
                    <input
                      value={folderCreateInput}
                      placeholder="例: ネットワーク/SBC"
                      onChange={(event) => setFolderCreateInput(event.target.value)}
                    />
                  </label>
                  <div className="module-folder-action-buttons">
                    <button className="primary" type="submit" disabled={!canCreateFolder}>
                      作成して関連付け
                    </button>
                    <button className="secondary" type="button" onClick={handleFolderCreateCancel}>
                      キャンセル
                    </button>
                  </div>
                </form>
              ) : null}
              <p className={"module-folder-action-message " + folderCreateState.status}>{folderCreateState.message}</p>
            </div>

            <div className="module-folder-action-card">
              <header>
                <h2>タグ名変更</h2>
                <span>操作対象: {selectedFolderLabel}</span>
              </header>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void handleFolderRenameSubmit();
                }}
              >
                <label>
                  新しいタグ名
                  <input
                    value={folderRenameInput}
                    disabled={folderPathFilter === ""}
                    placeholder="例: ネットワーク/SBC"
                    onChange={(event) => setFolderRenameInput(event.target.value)}
                  />
                </label>
                <button type="submit" className="primary" disabled={!canRenameFolder}>
                  名前を変更
                </button>
              </form>
              <p className={"module-folder-action-message " + folderRenameState.status}>
                {folderPathFilter === "" ? "左のタグ一覧から変更対象を選択してください。" : folderRenameState.message}
              </p>
            </div>

            <div className="module-folder-action-card">
              <header>
                <h2>選択済みモジュールへタグ追加</h2>
              </header>
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void handleFolderMoveSubmit();
                }}
              >
                <label>
                  追加するタグ
                  <select value={folderMoveTarget} onChange={(event) => setFolderMoveTarget(event.target.value)}>
                    {folderOptions.map((folder) => (
                      <option key={folder} value={folder}>
                        {folder === "未分類" ? "未分類（他の所属を解除）" : folder}
                      </option>
                    ))}
                  </select>
                </label>
                <button className="secondary" type="submit" disabled={!canMoveSelectedModules}>
                  タグを追加
                </button>
              </form>
              <p className={"module-folder-action-message " + folderMoveState.status}>{folderMoveState.message}</p>
            </div>
          </section>

          <Toolbar>
            <button className="secondary" onClick={() => navigate("/modules/search")}><span aria-hidden="true">↺</span>{"条件をリセット"}</button>
            <button className="primary" onClick={() => navigate("/modules/register")}><span aria-hidden="true">+</span>{"モジュール登録"}</button>
          </Toolbar>
          {moduleListState.status === "available" && moduleListState.items.length === 0 ? (
            <section className="empty-state"><h2>{"該当するモジュールはありません"}</h2><p>{"検索条件を変えて再度確認してください。"}</p></section>
          ) : (
            <DataTable
              columns={[
                <label className="module-row-select-all">
                  <input
                    type="checkbox"
                    checked={allVisibleModulesSelected}
                    onChange={toggleAllVisibleModules}
                    aria-label="表示中のモジュールをすべて選択"
                  />
                  選択
                </label>,
                "モジュールID",
                "モジュール名",
                "タグ",
                "版",
                "承認状態",
                "行数",
                "先頭作業",
                "作成者",
                "更新日",
                "操作",
              ]}
              rows={moduleListState.items.map((item) => [
                <input
                  type="checkbox"
                  checked={selectedModuleIds.includes(item.module_id)}
                  onChange={() => toggleSelectedModule(item.module_id)}
                  aria-label={item.module_key + " を選択"}
                />,
                item.module_key,
                item.module_name,
                <ModuleFolderMembershipList item={item} />,
                formatVersionLabel(item),
                <ModuleStatusPill status={item.status} label={item.status_label} />,
                item.row_count,
                item.first_work_text ?? "-",
                item.created_by ?? "-",
                item.updated_at,
                <button className="text-button" onClick={() => navigate("/modules/" + item.module_id)}>{"詳細"}</button>,
              ])}
            />
          )}
        </div>
      </div>
      {isFolderDeleteConfirmOpen ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setIsFolderDeleteConfirmOpen(false)}>
          <section
            aria-labelledby="folder-delete-dialog-title"
            aria-modal="true"
            className="modal-dialog"
            role="dialog"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <span className="modal-icon" aria-hidden="true">-</span>
            <h2 id="folder-delete-dialog-title">タグを削除しますか？</h2>
            <p>「{folderPathFilter}」を削除します。他にタグがないモジュールだけ「未分類」へ移動します。</p>
            <div className="modal-actions">
              <button className="secondary" type="button" onClick={() => setIsFolderDeleteConfirmOpen(false)}>
                キャンセル
              </button>
              <button className="danger" type="button" onClick={() => void handleFolderDeleteConfirm()}>
                削除する
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </Page>
  );
}

function ModuleListPage() {
  const location = useLocation();
  return <Navigate to={"/modules/search" + location.search} replace />;
}

function useModuleDetailState(moduleId: string | undefined, versionNo: string | null = null): ModuleDetailState {
  const [moduleDetailState, setModuleDetailState] = useState<ModuleDetailState>({
    status: "loading",
    item: null,
    message: "モジュール詳細を取得しています...",
  });

  useEffect(() => {
    if (!moduleId) {
      setModuleDetailState({
        status: "unavailable",
        item: null,
        message: "モジュールIDが指定されていません。",
      });
      return;
    }

    const abortController = new AbortController();

    setModuleDetailState({
      status: "loading",
      item: null,
      message: "モジュール詳細を取得しています...",
    });

    async function fetchModuleDetail(): Promise<void> {
      try {
        const endpoint = new URL(buildApiUrl(`/api/v1/modules/${moduleId}`), window.location.origin);
        if (versionNo !== null && versionNo.trim().length > 0) {
          endpoint.searchParams.set("version_no", versionNo);
        }
        const response = await fetch(endpoint.toString(), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<ModuleDetailData>;

        if (!response.ok || responseBody.result !== "success" || !responseBody.data) {
          setModuleDetailState({
            status: "unavailable",
            item: null,
            message: responseBody.message || `モジュール詳細の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        setModuleDetailState({
          status: "available",
          item: responseBody.data,
          message: responseBody.message || "モジュール詳細を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setModuleDetailState({
          status: "unavailable",
          item: null,
          message: "APIに接続できませんでした。",
        });
      }
    }

    void fetchModuleDetail();

    return () => {
      abortController.abort();
    };
  }, [moduleId, versionNo]);

  return moduleDetailState;
}

function ModuleDetailPage() {
  const navigate = useNavigate();
  const { moduleId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedVersionNo = searchParams.get("version_no");
  const moduleDetailState = useModuleDetailState(moduleId, selectedVersionNo);
  const item = moduleDetailState.item;
  const [isPreviewOverlayOpen, setIsPreviewOverlayOpen] = useState(false);
  const [versionListState, setVersionListState] = useState<ModuleVersionListState>({
    status: "idle",
    items: [],
    message: "モジュール版一覧は未取得です。",
  });
  const [moduleDiffState, setModuleDiffState] = useState<ModuleDiffState>({
    status: "idle",
    item: null,
    message: "比較元と比較先を選ぶと差分を確認できます。",
  });
  const [diffFromVersionNo, setDiffFromVersionNo] = useState<number | null>(null);
  const [diffToVersionNo, setDiffToVersionNo] = useState<number | null>(null);
  const versionOptions = [...versionListState.items].sort((a, b) => a.version_no - b.version_no);
  const nextVersionNo =
    versionListState.items.length > 0
      ? Math.max(...versionListState.items.map((version) => version.version_no)) + 1
      : item
        ? item.version_no + 1
        : 2;
  const hasInFlightVersion = versionListState.items.some((version) =>
    version.status === "draft" || version.status === "review_requested"
  );
  const isModuleLocked = item?.status === "review_requested";
  const canCreateSourceDoc = item?.status === "published";

  useEffect(() => {
    if (!moduleId) {
      return;
    }

    const abortController = new AbortController();

    async function fetchModuleVersions(): Promise<void> {
      setVersionListState({
        status: "loading",
        items: [],
        message: "モジュール版一覧を取得しています。",
      });

      try {
        const response = await fetch(buildApiUrl(`/api/v1/modules/${moduleId}/versions`), {
          signal: abortController.signal,
        });
        const responseBody = await readApiResponse<ModuleVersionListData>(response);

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setVersionListState({
            status: "unavailable",
            items: [],
            message: responseBody.message || `モジュール版一覧の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        setVersionListState({
          status: "available",
          items: responseBody.data.items,
          message: responseBody.message || "モジュール版一覧を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setVersionListState({
          status: "unavailable",
          items: [],
          message: "モジュール版一覧の取得中にAPI接続で失敗しました。",
        });
      }
    }

    void fetchModuleVersions();

    return () => {
      abortController.abort();
    };
  }, [moduleId]);

  useEffect(() => {
    const versionNos = versionOptions.map((version) => version.version_no);
    const previousVersionNo =
      item && versionNos.includes(item.version_no - 1)
        ? item.version_no - 1
        : item
          ? [...versionNos].reverse().find((versionNo) => versionNo < item.version_no) ?? null
          : null;

    setDiffFromVersionNo(previousVersionNo);
    setDiffToVersionNo(item?.version_no ?? null);
    setModuleDiffState({
      status: "idle",
      item: null,
      message: "比較元と比較先を選ぶと差分を確認できます。",
    });
  }, [item?.version_no, versionListState.items]);

  function handleVersionSelect(versionNo: number): void {
    setSearchParams({ version_no: String(versionNo) });
  }

  async function handleFetchModuleDiff(): Promise<void> {
    if (!item || !moduleId || diffFromVersionNo === null || diffToVersionNo === null) {
      return;
    }
    if (diffFromVersionNo === diffToVersionNo) {
      setModuleDiffState({
        status: "unavailable",
        item: null,
        message: "比較元と比較先には別の版を選んでください。",
      });
      return;
    }

    const fromVersionLabel = formatVersionLabel(
      versionOptions.find((version) => version.version_no === diffFromVersionNo) ?? { version_no: diffFromVersionNo },
    );
    const toVersionLabel = formatVersionLabel(
      versionOptions.find((version) => version.version_no === diffToVersionNo) ?? { version_no: diffToVersionNo },
    );

    setModuleDiffState({
      status: "loading",
      item: null,
      message: `${fromVersionLabel} と ${toVersionLabel} の差分を取得しています。`,
    });

    try {
      const endpoint = new URL(buildApiUrl(`/api/v1/modules/${moduleId}/diff`), window.location.origin);
      endpoint.searchParams.set("from_version", String(diffFromVersionNo));
      endpoint.searchParams.set("to_version", String(diffToVersionNo));
      const response = await fetch(endpoint.toString());
      const responseBody = await readApiResponse<ModuleDiffData>(response);

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setModuleDiffState({
          status: "unavailable",
          item: null,
          message: responseBody.message || `差分取得に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setModuleDiffState({
        status: "available",
        item: responseBody.data,
        message: responseBody.message || `${fromVersionLabel} と ${toVersionLabel} の差分を取得しました。`,
      });
    } catch (error) {
      setModuleDiffState({
        status: "unavailable",
        item: null,
        message: "差分取得中にAPI接続で失敗しました。",
      });
    }
  }

  return (
    <Page title="モジュール詳細" description="APIから取得したモジュールの基本情報と行データを確認します。">
      <section className={`list-status list-status-${moduleDetailState.status}`} aria-live="polite">
        <div>
          <span>取得状態</span>
          <strong>
            {moduleDetailState.status === "loading"
              ? "取得中"
              : moduleDetailState.status === "available"
                ? "取得完了"
                : "取得失敗"}
          </strong>
        </div>
        <div>
          <span>モジュールID</span>
          <strong>{moduleId ?? "指定なし"}</strong>
        </div>
        <div>
          <span>行数</span>
          <strong>{item ? item.row_count : "-"}</strong>
        </div>
        <p>{moduleDetailState.message}</p>
      </section>

      <Toolbar>
        <button className="secondary" onClick={() => navigate("/modules/list")}>
          <span aria-hidden="true">←</span>
          一覧へ戻る
        </button>
        <button className="secondary" onClick={() => setIsPreviewOverlayOpen(true)} disabled={!item}>
          <span aria-hidden="true">□</span>
          全画面プレビュー
        </button>
        <button
          className="secondary"
          onClick={() => {
            if (!item) {
              return;
            }
            const params = new URLSearchParams({
              mode: "new-version",
              module_id: String(item.module_id),
              module_key: item.module_key,
              module_name: item.module_name,
              next_version: String(nextVersionNo),
            });
            navigate(`/modules/register?${params.toString()}`);
          }}
          disabled={!item || isModuleLocked}
          title={
            isModuleLocked
              ? "承認依頼中のため新しい版を作成できません。"
              : hasInFlightVersion
                ? "既に作成中または承認依頼中の版がある場合、保存時にエラーになります。"
                : "Excelから新しい版を作成します。"
          }
        >
          <span aria-hidden="true">+</span>
          新しい版をExcelから作成
        </button>
        <button
          className="primary"
          onClick={() => item && navigate(`/documents/create?module_id=${item.module_id}`)}
          disabled={!canCreateSourceDoc}
          title={canCreateSourceDoc ? "このモジュールを選択した状態で原本作成へ進みます。" : "承認済みのモジュールだけを原本に利用できます。"}
        >
          <span aria-hidden="true">＋</span>
          このモジュールで原本作成
        </button>
      </Toolbar>

      {item ? (
        <>
          {isModuleLocked ? (
            <div className="approval-lock-note">
              <strong>承認依頼中です</strong>
              <span>承認者の確認待ちのため、このモジュール版は新しい版の作成対象にしません。</span>
            </div>
          ) : null}
          <section className="detail-layout">
            <div className="facts">
              <Fact label="モジュールID" value={item.module_key} />
              <Fact label="モジュール名" value={item.module_name} />
              <Fact label="版" value={formatVersionLabel(item)} />
              <Fact label="承認状態" value={item.status_label} />
              <Fact label="作成者" value={item.created_by ?? "-"} />
              <Fact label="更新日" value={item.updated_at} />
            </div>
            <div className="module-detail-note">
              <span>説明</span>
              <p>{item.description ?? "説明は未設定です。"}</p>
              <span>取込元</span>
              <p>{item.source_xlsx_path ?? "未設定"}</p>
            </div>
          </section>
          <ModuleVersionPanel
            currentVersionNo={item.version_no}
            state={versionListState}
            onSelectVersion={handleVersionSelect}
          />
          <section className="section-band">
            <div className="section-heading-row">
              <div>
                <h2>承認状態</h2>
                <p>承認依頼、承認、差戻し、保管は専用画面で行います。</p>
              </div>
              <ModuleStatusPill status={item.status} label={item.status_label} />
            </div>
            <Toolbar>
              <button className="secondary" type="button" onClick={() => navigate("/modules/approval")}>
                <span aria-hidden="true">→</span>
                モジュール承認状態確認へ
              </button>
            </Toolbar>
          </section>
          <ModuleDiffPanel
            currentVersionNo={item.version_no}
            versionOptions={versionOptions}
            fromVersionNo={diffFromVersionNo}
            toVersionNo={diffToVersionNo}
            state={moduleDiffState}
            onFromVersionChange={setDiffFromVersionNo}
            onToVersionChange={setDiffToVersionNo}
            onFetchDiff={handleFetchModuleDiff}
          />
        </>
      ) : (
        <section className="empty-state">
          <h2>モジュール詳細を表示できません</h2>
          <p>{moduleDetailState.message}</p>
        </section>
      )}

      {item && isPreviewOverlayOpen ? (
        <PreviewOverlay
          title={`${item.module_name.replace("_CS ", " ")} / 案件CSプレビュー`}
          description="添付Excelと同じ列構造で、装置が右方向に増える案件CS形式の全画面表示です。"
          onClose={() => setIsPreviewOverlayOpen(false)}
          actions={
            <button className="secondary" type="button" onClick={() => window.print()}>
              <span aria-hidden="true">P</span>
              印刷
            </button>
          }
        >
          <div className="preview-surface preview-surface-sheet">
            <ExcelModulePreview item={item} mode="fullscreen" />
          </div>
        </PreviewOverlay>
      ) : null}
    </Page>
  );
}

function ModuleVersionPanel({
  currentVersionNo,
  state,
  onSelectVersion,
}: {
  currentVersionNo: number;
  state: ModuleVersionListState;
  onSelectVersion: (versionNo: number) => void;
}) {
  return (
    <section className="section-band module-version-panel">
      <div className="section-heading-row">
        <div>
          <h2>版管理</h2>
          <p>{state.message}</p>
        </div>
        <strong>{state.items.length} 件</strong>
      </div>
      {state.items.length > 0 ? (
        <div className="module-version-list">
          {state.items.map((version) => (
            <button
              key={version.module_version_id}
              type="button"
              className={version.version_no === currentVersionNo ? "module-version-card active" : "module-version-card"}
              onClick={() => onSelectVersion(version.version_no)}
            >
              <span>{formatVersionLabel(version)}</span>
              <ModuleStatusPill status={version.status} label={version.status_label} />
              <small>{`${version.row_count} 行 / ${version.updated_at}`}</small>
            </button>
          ))}
        </div>
      ) : (
        <p>表示できる版はありません。</p>
      )}
    </section>
  );
}

function ModuleDiffPanel({
  currentVersionNo,
  versionOptions,
  fromVersionNo,
  toVersionNo,
  state,
  onFromVersionChange,
  onToVersionChange,
  onFetchDiff,
}: {
  currentVersionNo: number;
  versionOptions: ModuleVersionListItemData[];
  fromVersionNo: number | null;
  toVersionNo: number | null;
  state: ModuleDiffState;
  onFromVersionChange: (versionNo: number | null) => void;
  onToVersionChange: (versionNo: number | null) => void;
  onFetchDiff: () => void;
}) {
  const changedRows = state.item?.rows.filter((row) => row.status !== "unchanged") ?? [];
  const unchangedCount = state.item?.rows.filter((row) => row.status === "unchanged").length ?? 0;
  const fromVersion = versionOptions.find((version) => version.version_no === fromVersionNo) ?? null;
  const toVersion = versionOptions.find((version) => version.version_no === toVersionNo) ?? null;
  const currentVersion = versionOptions.find((version) => version.version_no === currentVersionNo) ?? null;
  const canFetchDiff =
    fromVersionNo !== null
    && toVersionNo !== null
    && fromVersionNo !== toVersionNo
    && state.status !== "loading";

  return (
    <section className="section-band module-diff-panel">
      <div className="section-heading-row">
        <div>
          <h2>版の差分</h2>
          <p>{state.message}</p>
        </div>
        <button
          className="secondary"
          type="button"
          onClick={onFetchDiff}
          disabled={!canFetchDiff}
        >
          差分を見る
        </button>
      </div>
      <div className="module-diff-selector-grid">
        <label>
          比較元
          <select
            value={fromVersionNo ?? ""}
            onChange={(event) => onFromVersionChange(event.target.value === "" ? null : Number(event.target.value))}
          >
            <option value="">未選択</option>
            {versionOptions.map((version) => (
              <option key={`from-${version.module_version_id}`} value={version.version_no}>
                {formatDiffVersionLabel(version)}
              </option>
            ))}
          </select>
        </label>
        <label>
          比較先
          <select
            value={toVersionNo ?? ""}
            onChange={(event) => onToVersionChange(event.target.value === "" ? null : Number(event.target.value))}
          >
            <option value="">未選択</option>
            {versionOptions.map((version) => (
              <option key={`to-${version.module_version_id}`} value={version.version_no}>
                {formatDiffVersionLabel(version)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="module-diff-meta">
        <Fact label="比較元" value={fromVersion === null ? "-" : formatDiffVersionLabel(fromVersion)} />
        <Fact label="比較先" value={toVersion === null ? "-" : formatDiffVersionLabel(toVersion)} />
        <Fact label="表示中の版" value={currentVersion === null ? `ver.${currentVersionNo}.0` : formatDiffVersionLabel(currentVersion)} />
      </div>
      {state.item ? (
        <>
          <div className="module-diff-summary">
            <Fact label="追加" value={String(state.item.summary.added_count)} />
            <Fact label="削除" value={String(state.item.summary.removed_count)} />
            <Fact label="変更" value={String(state.item.summary.changed_count)} />
            <Fact label="変更なし" value={String(state.item.summary.unchanged_count)} />
          </div>
          {changedRows.length > 0 ? (
            <div className="module-diff-list" aria-label="変更行一覧">
              {changedRows.map((row, index) => (
                <ModuleDiffRowCard row={row} key={`${row.status}-${row.row_key}-${index}`} />
              ))}
            </div>
          ) : (
            <div className="module-diff-empty">
              <strong>差分はありません</strong>
              <span>{`${fromVersion === null ? `ver.${state.item.from_version}.0` : formatDiffVersionLabel(fromVersion)} と ${toVersion === null ? `ver.${state.item.to_version}.0` : formatDiffVersionLabel(toVersion)} の手順行は一致しています。`}</span>
            </div>
          )}
          {unchangedCount > 0 ? (
            <p className="form-hint">{`変更なしの行 ${unchangedCount} 件は省略表示しています。`}</p>
          ) : null}
        </>
      ) : versionOptions.length < 2 ? (
        <p>比較できる版が2つ以上ありません。</p>
      ) : fromVersionNo === toVersionNo ? (
        <p>比較元と比較先には別の版を選んでください。</p>
      ) : null}
    </section>
  );
}

function getModuleDiffStatusLabel(statusValue: ModuleDiffRowData["status"]): string {
  const labels: Record<ModuleDiffRowData["status"], string> = {
    added: "追加",
    removed: "削除",
    changed: "変更",
    unchanged: "変更なし",
  };
  return labels[statusValue];
}

function getModuleDiffStatusDescription(statusValue: ModuleDiffRowData["status"]): string {
  const descriptions: Record<ModuleDiffRowData["status"], string> = {
    added: "新しい版で追加された行",
    removed: "新しい版では削除された行",
    changed: "前版から内容が変わった行",
    unchanged: "変更なし",
  };
  return descriptions[statusValue];
}

function getModuleDiffChangedFieldLabel(fieldName: string): string {
  const labels: Record<string, string> = {
    row_type: "行種別",
    major_no: "大番号",
    middle_no: "中番号",
    minor_no: "小番号",
    tech_doc_text: "技術資料名",
    work_text: "作業内容",
    indent_level: "インデント",
    expected_result: "確認事項",
    time_text: "時刻",
    window_text: "window",
    p_text: "P",
    command_text: "コマンド",
    note: "備考",
    device_entries: "装置別入力",
    images: "画像",
  };
  return labels[fieldName] ?? fieldName;
}

function getModuleSimilarityMatchedFieldLabel(fieldName: string): string {
  const labels: Record<string, string> = {
    work_text: "作業内容",
    expected_result: "確認事項",
    command: "コマンド",
    name: "モジュール名",
    structure: "行構造",
    device_header: "対象装置",
  };
  return labels[fieldName] ?? fieldName;
}

function getModuleDiffRowNumber(row: ModuleDetailRowData | null): string {
  if (row === null) {
    return "-";
  }

  const numbers = [row.major_no, row.middle_no, row.minor_no].filter(Boolean);
  return numbers.length > 0 ? numbers.join("-") : `行${row.row_order}`;
}

function getModuleDiffExcelRowLabel(row: ModuleDetailRowData | null): string {
  if (row === null) {
    return "-";
  }
  return `${row.row_order}行目`;
}

function getModuleDiffRowText(row: ModuleDetailRowData | null): string {
  if (row === null) {
    return "-";
  }
  return row.work_text || row.expected_result || row.command_text || row.tech_doc_text || "(空行)";
}

function getModuleDiffRowSecondaryText(row: ModuleDetailRowData | null): string {
  if (row === null) {
    return "-";
  }

  const values = [
    row.tech_doc_text ? `技術資料: ${row.tech_doc_text}` : null,
    row.expected_result ? `確認: ${row.expected_result}` : null,
    row.command_text ? `コマンド: ${row.command_text}` : null,
  ].filter(Boolean);
  return values.length > 0 ? values.join(" / ") : "補足情報なし";
}

function getModuleDiffDeviceSummary(row: ModuleDetailRowData | null): string {
  if (row === null || row.device_entries.length === 0) {
    return "装置別入力なし";
  }

  return row.device_entries
    .map((entry) => {
      const values = [entry.window_text, entry.p_text, entry.command_text].filter(Boolean).join(" ");
      return `装置${entry.slot_no}: ${values || "-"}`;
    })
    .join(" / ");
}

function getModuleDiffImageSummary(row: ModuleDetailRowData | null): string {
  if (row === null || row.images.length === 0) {
    return "画像なし";
  }

  return `${row.images.length}枚: ${row.images.map((image) => image.anchor_cell).join(", ")}`;
}

function ModuleDiffRowCard({ row }: { row: ModuleDiffRowData }) {
  const beforeLabel = row.before ? getModuleDiffRowNumber(row.before) : "-";
  const afterLabel = row.after ? getModuleDiffRowNumber(row.after) : "-";
  const beforeExcelRowLabel = getModuleDiffExcelRowLabel(row.before);
  const afterExcelRowLabel = getModuleDiffExcelRowLabel(row.after);
  const primaryExcelRowLabel =
    row.status === "removed" ? beforeExcelRowLabel : row.status === "added" ? afterExcelRowLabel : afterExcelRowLabel;
  const changedFieldLabels = row.changed_fields.map(getModuleDiffChangedFieldLabel);

  return (
    <article className={`module-diff-card module-diff-card-${row.status}`}>
      <div className="module-diff-card-header">
        <span className={`module-diff-status module-diff-status-${row.status}`}>
          {getModuleDiffStatusLabel(row.status)}
        </span>
        <span className="module-diff-row-badge">{`Excel ${primaryExcelRowLabel}`}</span>
        <div>
          <strong>{getModuleDiffStatusDescription(row.status)}</strong>
          <small>{`番号 前: ${beforeLabel} / 後: ${afterLabel}`}</small>
          <small>{`Excel行 前: ${beforeExcelRowLabel} / 後: ${afterExcelRowLabel}`}</small>
        </div>
      </div>
      {changedFieldLabels.length > 0 ? (
        <div className="module-diff-chips" aria-label="変更項目">
          {changedFieldLabels.map((label) => (
            <span key={label}>{label}</span>
          ))}
        </div>
      ) : row.status !== "changed" ? (
        <div className="module-diff-chips" aria-label="変更項目">
          <span>行全体</span>
        </div>
      ) : null}
      <div className="module-diff-comparison">
        <ModuleDiffRowSnapshot label="変更前" row={row.before} tone="before" />
        <ModuleDiffRowSnapshot label="変更後" row={row.after} tone="after" />
      </div>
    </article>
  );
}

function ModuleDiffRowSnapshot({
  label,
  row,
  tone,
}: {
  label: string;
  row: ModuleDetailRowData | null;
  tone: "before" | "after";
}) {
  return (
    <div className={`module-diff-snapshot module-diff-snapshot-${tone}`}>
      <span>{label}</span>
      <strong>{getModuleDiffRowText(row)}</strong>
      <small>{getModuleDiffRowSecondaryText(row)}</small>
      <small>{getModuleDiffDeviceSummary(row)}</small>
      <small>{getModuleDiffImageSummary(row)}</small>
    </div>
  );
}

function ModuleSimilarityReview({
  state,
  registrationConfirmed,
  diffState,
  diffCandidate,
  downloadState,
  onShowDiff,
  onDownloadDiff,
  onContinue,
  onCancel,
}: {
  state: ModuleSimilarityCheckState;
  registrationConfirmed: boolean;
  diffState: ModuleDiffState;
  diffCandidate: ModuleSimilarityCandidateData | null;
  downloadState: ModuleSimilarityDiffDownloadState;
  onShowDiff: (candidate: ModuleSimilarityCandidateData) => void;
  onDownloadDiff: (candidate: ModuleSimilarityCandidateData) => void;
  onContinue: () => void;
  onCancel: () => void;
}) {
  const item = state.item;
  const hasCandidates = (item?.candidate_count ?? 0) > 0;
  const changedRows = diffState.item?.rows.filter((row) => row.status !== "unchanged") ?? [];

  return (
    <section className="register-step-card module-similarity-review">
      <div className="register-step-header">
        <div>
          <h2>類似モジュール確認</h2>
          <p className="register-section-copy">
            承認済みモジュールと比較し、類似度が {Math.round((item?.threshold ?? 0.7) * 100)}% 以上の候補を表示します。
          </p>
        </div>
        {state.status === "success" ? (
          <span className={hasCandidates ? "module-similarity-count warning" : "module-similarity-count clear"}>
            {hasCandidates ? `${item?.candidate_count ?? 0}件の候補` : "候補なし"}
          </span>
        ) : null}
      </div>

      <section
        className={`register-status ${
          state.status === "success"
            ? hasCandidates
              ? "register-status-submitting"
              : "register-status-success"
            : state.status === "error"
              ? "register-status-error"
              : state.status === "submitting"
                ? "register-status-submitting"
                : ""
        }`}
        aria-live="polite"
      >
        <span>確認状態</span>
        <strong>
          {state.status === "success"
            ? hasCandidates
              ? "確認が必要"
              : "確認完了"
            : state.status === "error"
              ? "確認失敗"
              : state.status === "submitting"
                ? "確認中"
                : "未確認"}
        </strong>
        <p>{state.message}</p>
        {item ? (
          <div className="register-result-meta">
            <span>{`比較対象 ${item.checked_count}件`}</span>
            <span>{`判定基準 ${Math.round(item.threshold * 100)}%`}</span>
            {item.exact_match ? <span>完全一致あり</span> : null}
          </div>
        ) : null}
      </section>

      {item && item.candidates.length > 0 ? (
        <>
          <div className="module-similarity-table" role="table" aria-label="類似モジュール候補">
            <div className="module-similarity-table-header" role="row">
              <span role="columnheader">類似度</span>
              <span role="columnheader">候補モジュール</span>
              <span role="columnheader">一致傾向</span>
              <span role="columnheader">操作</span>
            </div>
            {item.candidates.map((candidate) => (
              <div className="module-similarity-table-row" role="row" key={candidate.module_version_id}>
                <div role="cell">
                  <strong className="module-similarity-score">{`${Math.round(candidate.similarity * 100)}%`}</strong>
                  {candidate.exact_match ? <span className="module-similarity-exact">完全一致</span> : null}
                </div>
                <div role="cell">
                  <strong>{`${candidate.module_key} / ${candidate.module_name}`}</strong>
                  <small>{`${candidate.version_label} / 承認済み`}</small>
                </div>
                <div role="cell">
                  <span>
                    {candidate.matched_fields.length > 0
                      ? candidate.matched_fields.map(getModuleSimilarityMatchedFieldLabel).join(" / ")
                      : "一致項目なし"}
                  </span>
                </div>
                <div role="cell">
                  <div className="module-similarity-row-actions">
                    <button
                      className="secondary"
                      type="button"
                      onClick={() => onShowDiff(candidate)}
                      disabled={
                        diffState.status === "loading"
                        && diffCandidate?.module_version_id === candidate.module_version_id
                      }
                    >
                      差分を見る
                    </button>
                    <button
                      className="secondary"
                      type="button"
                      onClick={() => onDownloadDiff(candidate)}
                      disabled={
                        downloadState.status === "loading"
                        && downloadState.candidateId === candidate.module_version_id
                      }
                    >
                      {downloadState.status === "loading"
                      && downloadState.candidateId === candidate.module_version_id
                        ? "作成中..."
                        : "差分Excel"}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {downloadState.status !== "idle" ? (
            <p
              className={`module-similarity-download-status ${downloadState.status}`}
              aria-live="polite"
            >
              {downloadState.message}
            </p>
          ) : null}

          <div className="module-similarity-actions">
            <button className="danger" type="button" onClick={onCancel}>
              登録を中止
            </button>
            <button
              className="primary"
              type="button"
              onClick={onContinue}
              disabled={registrationConfirmed || !item.confirmation_token}
            >
              {registrationConfirmed ? "登録続行を選択済み" : "登録を続ける"}
            </button>
          </div>
          {registrationConfirmed ? (
            <p className="module-similarity-confirmed">類似候補を確認したうえで、登録を続けます。</p>
          ) : (
            <p className="module-similarity-warning">差分を確認し、登録を続けるか中止するか選択してください。</p>
          )}
        </>
      ) : null}

      {diffCandidate ? (
        <section className="module-similarity-diff" aria-live="polite">
          <div className="section-heading-row">
            <div>
              <h3>{`${diffCandidate.module_key} との行差分`}</h3>
              <p>{diffState.message}</p>
            </div>
            {diffState.item ? (
              <div className="module-similarity-diff-summary">
                <span>{`追加 ${diffState.item.summary.added_count}`}</span>
                <span>{`削除 ${diffState.item.summary.removed_count}`}</span>
                <span>{`変更 ${diffState.item.summary.changed_count}`}</span>
              </div>
            ) : null}
          </div>
          {diffState.status === "loading" ? <p>差分を読み込んでいます...</p> : null}
          {diffState.item && changedRows.length > 0 ? (
            <div className="module-diff-list" aria-label="類似候補との差分">
              {changedRows.map((row, index) => (
                <ModuleDiffRowCard row={row} key={`${row.status}-${row.row_key}-${index}`} />
              ))}
            </div>
          ) : diffState.item ? (
            <div className="module-diff-empty">
              <strong>行差分はありません</strong>
              <span>取込内容と候補モジュールの手順行は一致しています。</span>
            </div>
          ) : null}
        </section>
      ) : null}
    </section>
  );
}

function ExcelModulePreview({
  item,
  mode = "embedded",
}: {
  item: ModuleDetailData;
  mode?: "embedded" | "fullscreen";
}) {
  const rowsWithIndent = buildIndentedRows(item.rows);
  const deviceHeaders = getModuleDeviceHeaders(item);

  if (mode === "fullscreen") {
    return <ExcelModuleCaseSheet item={item} rowsWithIndent={rowsWithIndent} deviceHeaders={deviceHeaders} />;
  }

  return (
    <section className="excel-preview" aria-label="Excel風モジュールプレビュー">
      <div className="excel-device-summary">
        <div className="excel-device-summary-card excel-device-summary-title">
          <span>モジュール</span>
          <strong>{item.module_name.replace("_CS ", " ")}</strong>
        </div>
        {deviceHeaders.map((header) => (
          <div key={header.slot_no} className="excel-device-summary-card">
            <span>{`装置 ${header.slot_no}`}</span>
            <strong>{header.target_device_text ?? "-"}</strong>
            <dl>
              <div>
                <dt>時刻</dt>
                <dd>{header.header_time_text ?? "-"}</dd>
              </div>
              <div>
                <dt>target</dt>
                <dd>{header.target_text ?? "-"}</dd>
              </div>
              <div>
                <dt>P</dt>
                <dd>{header.p_text ?? "-"}</dd>
              </div>
            </dl>
          </div>
        ))}
      </div>

      <div className="excel-sheet-wrap">
        <table className="excel-sheet">
          <colgroup>
            <col className="excel-col-small" />
            <col className="excel-col-small" />
            <col className="excel-col-small" />
            <col className="excel-col-doc" />
            <col className="excel-col-work" />
            <col className="excel-col-check" />
          </colgroup>
          <thead>
            <tr>
              <th>大</th>
              <th>中</th>
              <th>小</th>
              <th>技術資料名</th>
              <th>作業内容</th>
              <th>確認事項 / 項目</th>
            </tr>
          </thead>
          <tbody>
            {rowsWithIndent.map(({ row, indentLevel }) => (
              <tr key={row.module_row_id} className={`excel-row excel-row-${row.row_type}`}>
                <td className="excel-number">{row.major_no ?? ""}</td>
                <td className="excel-number">{row.middle_no ?? ""}</td>
                <td className="excel-number">{row.minor_no ?? ""}</td>
                <td>{row.tech_doc_text ?? ""}</td>
                <td className="excel-work-cell">
                  <IndentedExcelText text={row.work_text} indentLevel={indentLevel} />
                  <ModuleRowImageList images={row.images ?? []} placement="work" />
                </td>
                <td>
                  <IndentedExcelText text={row.expected_result} indentLevel={0} />
                  <ModuleRowImageList images={row.images ?? []} placement="expected" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ExcelModuleCaseSheet({
  item,
  rowsWithIndent,
  deviceHeaders,
}: {
  item: ModuleDetailData;
  rowsWithIndent: Array<{ row: ModuleDetailRowData; indentLevel: 0 | 1 | 2 | 3 | 4 }>;
  deviceHeaders: ModuleDeviceHeaderData[];
}) {
  const caseTitle = item.module_name.replace("_CS ", " ");
  const caseDeviceHeaders =
    deviceHeaders.length > 0
      ? deviceHeaders
      : [
          {
            slot_no: 1,
            header_time_text: item.header_time_text,
            target_text: item.target_text,
            p_text: item.common_p_text,
            target_device_text: item.target_device_text,
          },
        ];
  const totalColumnSpan = 9 + caseDeviceHeaders.length * 4;

  return (
    <section className="excel-preview excel-preview-fullscreen" aria-label="案件CSプレビュー">
      <div className="excel-sheet-wrap excel-sheet-wrap-case excel-sheet-scroll-with-sticky-left excel-sheet-scroll-case">
        <table className="excel-sheet excel-sheet-case excel-sheet-multi-device excel-sheet-sticky-left excel-sheet-case-sticky">
          <colgroup>
            <col className="excel-col-small" />
            <col className="excel-col-small" />
            <col className="excel-col-small" />
            <col className="excel-col-doc" />
            <col className="excel-col-work-block" />
            <col className="excel-col-work-block" />
            <col className="excel-col-work-block" />
            <col className="excel-col-work-block" />
            <col className="excel-col-check" />
            {caseDeviceHeaders.map((header) => (
              <Fragment key={`cols-${header.slot_no}`}>
                <col className="excel-col-time" />
                <col className="excel-col-window" />
                <col className="excel-col-prompt" />
                <col className="excel-col-command" />
              </Fragment>
            ))}
          </colgroup>
          <tbody>
            <tr className="excel-case-title-row">
              <td colSpan={9} className="excel-case-title-cell">
                {caseTitle}
              </td>
              {caseDeviceHeaders.map((header, deviceIndex) => {
                const deviceToneClass = deviceIndex % 2 === 0 ? "excel-device-block-odd" : "excel-device-block-even";
                return (
                  <Fragment key={`top-label-${header.slot_no}`}>
                    <td className={`excel-case-top-label ${deviceToneClass}`}>時刻</td>
                    <td className={`excel-case-top-label ${deviceToneClass}`}>terget</td>
                    <td className={`excel-case-top-label ${deviceToneClass}`}>P</td>
                    <td className={`excel-case-top-label ${deviceToneClass}`}>対象装置</td>
                  </Fragment>
                );
              })}
            </tr>
            <tr className="excel-case-device-meta-row">
              <td colSpan={9} className="excel-case-left-blank" />
              {caseDeviceHeaders.map((header, deviceIndex) => {
                const deviceToneClass = deviceIndex % 2 === 0 ? "excel-device-block-odd" : "excel-device-block-even";
                return (
                  <Fragment key={`top-value-${header.slot_no}`}>
                    <td className={`excel-center ${deviceToneClass}`}>{header.header_time_text ?? ""}</td>
                    <td className={deviceToneClass}>{header.target_text ?? String(header.slot_no)}</td>
                    <td className={`excel-center ${deviceToneClass}`}>{header.p_text ?? ""}</td>
                    <td className={deviceToneClass}>{header.target_device_text ?? `device-${String(header.slot_no).padStart(2, "0")}`}</td>
                  </Fragment>
                );
              })}
            </tr>
            <tr className="excel-case-spacer-row">
              <td colSpan={totalColumnSpan} />
            </tr>
            <tr className="excel-case-group-row">
              <td colSpan={3} className="excel-case-group-cell">通番</td>
              <td className="excel-case-group-cell" />
              <td colSpan={4} className="excel-case-group-cell">作業内容</td>
              <td className="excel-case-group-cell" />
              {caseDeviceHeaders.map((header, deviceIndex) => {
                const deviceToneClass = deviceIndex % 2 === 0 ? "excel-device-block-odd" : "excel-device-block-even";
                return (
                  <Fragment key={`group-${header.slot_no}`}>
                    <td className={`excel-case-group-cell ${deviceToneClass}`} />
                    <td className={`excel-case-group-cell ${deviceToneClass}`} />
                    <td className={`excel-case-group-cell ${deviceToneClass}`} />
                    <td className={`excel-case-device-name ${deviceToneClass}`}>{header.target_device_text ?? `{{DEVICE_${header.slot_no}}}`}</td>
                  </Fragment>
                );
              })}
            </tr>
            <tr>
              <th>大</th>
              <th>中</th>
              <th>小</th>
              <th>技術資料名</th>
              <th colSpan={4}>作業内容</th>
              <th>確認事項 or 項目</th>
              {caseDeviceHeaders.map((header, deviceIndex) => {
                const deviceToneClass = deviceIndex % 2 === 0 ? "excel-device-block-odd" : "excel-device-block-even";
                return (
                  <Fragment key={`header-${header.slot_no}`}>
                    <th className={deviceToneClass}>時刻</th>
                    <th className={deviceToneClass}>window</th>
                    <th className={deviceToneClass}>P</th>
                    <th className={deviceToneClass}>コマンド</th>
                  </Fragment>
                );
              })}
            </tr>
            {rowsWithIndent.map(({ row, indentLevel }) => (
              <tr key={row.module_row_id} className={`excel-row excel-row-${row.row_type}`}>
                <td className="excel-number">{row.major_no ?? ""}</td>
                <td className="excel-number">{row.middle_no ?? ""}</td>
                <td className="excel-number">{row.minor_no ?? ""}</td>
                <td>{row.tech_doc_text ?? ""}</td>
                <td colSpan={4} className="excel-work-cell excel-work-cell-wide">
                  <IndentedExcelText text={row.work_text} indentLevel={indentLevel} />
                  <ModuleRowImageList images={row.images ?? []} placement="work" />
                </td>
                <td>
                  <IndentedExcelText text={row.expected_result} indentLevel={0} />
                  <ModuleRowImageList images={row.images ?? []} placement="expected" />
                </td>
                {caseDeviceHeaders.map((header) => {
                  const entry = getModuleDeviceEntry(row, header.slot_no);
                  return (
                    <Fragment key={`${row.module_row_id}-${header.slot_no}`}>
                      <td className="excel-center">{getModuleDeviceEntryValue(row, entry, "time_text")}</td>
                      <td>{getModuleDeviceEntryValue(row, entry, "window_text")}</td>
                      <td>{getModuleDeviceEntryValue(row, entry, "p_text")}</td>
                      <td className="excel-command-cell">{getModuleDeviceEntryValue(row, entry, "command_text")}</td>
                    </Fragment>
                  );
                })}
              </tr>
            ))}
            <tr className="excel-case-spacer-row">
              <td colSpan={totalColumnSpan} />
            </tr>
            <tr className="excel-case-remarks-row">
              <td colSpan={totalColumnSpan}>
                <strong>備考</strong>
                <p>{item.description ?? ""}</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ModuleRegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const versionSourceModuleId = searchParams.get("module_id");
  const versionSourceModuleKey = searchParams.get("module_key");
  const versionSourceModuleName = searchParams.get("module_name");
  const versionNextVersion = searchParams.get("next_version");
  const isNewVersionMode = searchParams.get("mode") === "new-version" && versionSourceModuleKey !== null;
  const [moduleKeyInput, setModuleKeyInput] = useState("");
  const [moduleNameInput, setModuleNameInput] = useState("初期点検手順");
  const [descriptionInput, setDescriptionInput] = useState("モジュール登録画面から作成。");
  const [sourcePathInput, setSourcePathInput] = useState("imports/manual-module.xlsx");
  const [createdByInput, setCreatedByInput] = useState("webui");
  const [deviceHeaders, setDeviceHeaders] = useState<ModuleRegisterDeviceHeaderDraft[]>([
    {
      slotNo: 1,
      headerTimeText: "09:00",
      targetText: "CS",
      pText: ">",
      targetDeviceText: "device-01",
    },
  ]);
  const [rowSeed, setRowSeed] = useState(2);
  const [rows, setRows] = useState<ModuleRegisterRowDraft[]>([
    {
      rowId: 1,
      rowType: "step",
      indentLevel: 0,
      majorNo: "1",
      middleNo: "1",
      minorNo: "1",
      techDocText: "技術資料",
      workText: "作業前確認。",
      expectedResult: "準備完了。",
      deviceEntries: [
        {
          slotNo: 1,
          timeText: "5分",
          windowText: "コンソール",
          pText: ">",
          commandText: "show version",
        },
      ],
      images: [],
    },
  ]);
  const [createState, setCreateState] = useState<ModuleCreateState>({
    status: "idle",
    item: null,
    message: "装置ブロックと手順行を入力して、初版モジュールを保存してください。",
  });

  const [importPreviewState, setImportPreviewState] = useState<ModuleImportPreviewState>({
    status: "idle",
    item: null,
    message: "Excel取込プレビューはまだ実行していません。",
  });

  function updateRow(rowId: number, field: keyof ModuleRegisterRowDraft, value: string | number): void {
    setRows((currentRows) =>
      currentRows.map((row) => (row.rowId === rowId ? { ...row, [field]: value } : row)),
    );
  }

  function updateDeviceHeader(
    slotNo: number,
    field: keyof Omit<ModuleRegisterDeviceHeaderDraft, "slotNo">,
    value: string,
  ): void {
    setDeviceHeaders((currentHeaders) =>
      currentHeaders.map((header) => (header.slotNo === slotNo ? { ...header, [field]: value } : header)),
    );
  }

  function updateRowDeviceEntry(
    rowId: number,
    slotNo: number,
    field: keyof Omit<ModuleRegisterDeviceEntryDraft, "slotNo">,
    value: string,
  ): void {
    setRows((currentRows) =>
      currentRows.map((row) =>
        row.rowId === rowId
          ? {
              ...row,
              deviceEntries: row.deviceEntries.map((entry) =>
                entry.slotNo === slotNo ? { ...entry, [field]: value } : entry,
              ),
            }
          : row,
      ),
    );
  }

  function getRegisterRowDeviceEntry(
    row: ModuleRegisterRowDraft,
    slotNo: number,
  ): ModuleRegisterDeviceEntryDraft {
    return (
      row.deviceEntries.find((candidate) => candidate.slotNo === slotNo) ?? {
        slotNo,
        timeText: "",
        windowText: "",
        pText: "",
        commandText: "",
      }
    );
  }

  function addDeviceSlot(): void {
    setDeviceHeaders((currentHeaders) => {
      if (currentHeaders.length >= 20) {
        return currentHeaders;
      }

      const nextSlotNo = Math.max(...currentHeaders.map((header) => header.slotNo)) + 1;
      setRows((currentRows) =>
        currentRows.map((row) => ({
          ...row,
          deviceEntries: [
            ...row.deviceEntries,
            {
              slotNo: nextSlotNo,
              timeText: "",
              windowText: "",
              pText: "",
              commandText: "",
            },
          ],
        })),
      );
      return [
        ...currentHeaders,
        {
          slotNo: nextSlotNo,
          headerTimeText: "",
          targetText: "",
          pText: "",
          targetDeviceText: `device-${String(nextSlotNo).padStart(2, "0")}`,
        },
      ];
    });
  }

  function removeDeviceSlot(slotNo: number): void {
    setDeviceHeaders((currentHeaders) => {
      if (currentHeaders.length === 1) {
        return currentHeaders;
      }

      setRows((currentRows) =>
        currentRows.map((row) => ({
          ...row,
          deviceEntries: row.deviceEntries.filter((entry) => entry.slotNo !== slotNo),
        })),
      );
      return currentHeaders.filter((header) => header.slotNo !== slotNo);
    });
  }

  function addRow(): void {
    setRows((currentRows) => [
      ...currentRows,
      {
        rowId: rowSeed,
        rowType: "step",
        indentLevel: 0,
        majorNo: "",
        middleNo: "",
        minorNo: "",
        techDocText: "",
        workText: "",
        expectedResult: "",
        deviceEntries: deviceHeaders.map((header) => ({
          slotNo: header.slotNo,
          timeText: "",
          windowText: "",
          pText: "",
          commandText: "",
        })),
        images: [],
      },
    ]);
    setRowSeed((currentSeed) => currentSeed + 1);
  }

  function removeRow(rowId: number): void {
    setRows((currentRows) => (currentRows.length > 1 ? currentRows.filter((row) => row.rowId !== rowId) : currentRows));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    setCreateState({
      status: "submitting",
      item: null,
      message: "複数装置対応のモジュールを保存しています...",
    });

    try {
      const response = await fetch(buildApiUrl("/api/v1/modules"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          module_key: moduleKeyInput.trim() || undefined,
          module_name: moduleNameInput.trim(),
          description: descriptionInput.trim() || undefined,
          source_xlsx_path: sourcePathInput.trim() || undefined,
          created_by: createdByInput.trim() || undefined,
          device_headers: deviceHeaders.map((header) => ({
            slot_no: header.slotNo,
            header_time_text: header.headerTimeText.trim() || undefined,
            target_text: header.targetText.trim() || undefined,
            p_text: header.pText.trim() || undefined,
            target_device_text: header.targetDeviceText.trim() || undefined,
          })),
          rows: rows.map((row, index) => ({
            row_order: index + 1,
            row_type: "step",
            major_no: row.majorNo.trim() || undefined,
            middle_no: row.middleNo.trim() || undefined,
            minor_no: row.minorNo.trim() || undefined,
            tech_doc_text: row.techDocText.trim() || undefined,
            work_text: row.workText.trim() || undefined,
            indent_level: row.indentLevel,
            expected_result: row.expectedResult.trim() || undefined,
            device_entries: row.deviceEntries.map((entry) => ({
              slot_no: entry.slotNo,
              time_text: entry.timeText.trim() || undefined,
              window_text: entry.windowText.trim() || undefined,
              p_text: entry.pText.trim() || undefined,
              command_text: entry.commandText.trim() || undefined,
            })),
            images: row.images,
          })),
        }),
      });

      const responseBody = await readApiResponse<ModuleDetailData>(response);

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setCreateState({
          status: "error",
          item: null,
          message: responseBody.message || `モジュール登録に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setCreateState({
        status: "success",
        item: responseBody.data,
        message: responseBody.message || "モジュールを登録しました。",
      });
      setModuleKeyInput(responseBody.data.module_key);
    } catch (error) {
      setCreateState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : "モジュール登録に失敗しました。",
      });
    }
  }

  async function handleImportPreview(): Promise<void> {
    setImportPreviewState({
      status: "submitting",
      item: null,
      message: "Excel取込プレビューを実行しています。",
    });

    try {
      const response = await fetch(buildApiUrl("/api/v1/modules/import-sheet"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          module_key: moduleKeyInput.trim() || undefined,
          module_name: moduleNameInput.trim(),
          description: descriptionInput.trim() || undefined,
          change_note: "登録画面からプレビュー",
          source_xlsx_path: sourcePathInput.trim() || undefined,
          created_by: createdByInput.trim() || undefined,
          device_header_cells: deviceHeaders.map((header) => ({
            slot_no: header.slotNo,
            header_time_text: header.headerTimeText.trim() || undefined,
            target_text: header.targetText.trim() || undefined,
            p_text: header.pText.trim() || undefined,
            target_device_text: header.targetDeviceText.trim() || undefined,
          })),
          row_cells: rows.map((row) => ({
            A: row.majorNo.trim() || undefined,
            B: row.middleNo.trim() || undefined,
            C: row.minorNo.trim() || undefined,
            D: row.techDocText.trim() || undefined,
            [["E", "F", "G", "H"][row.indentLevel] ?? "E"]: row.workText.trim() || undefined,
            I: row.expectedResult.trim() || undefined,
            device_entries: row.deviceEntries.map((entry) => ({
              slot_no: entry.slotNo,
              time_text: entry.timeText.trim() || undefined,
              window_text: entry.windowText.trim() || undefined,
              p_text: entry.pText.trim() || undefined,
              command_text: entry.commandText.trim() || undefined,
            })),
          })),
        }),
      });

      const responseBody = await readApiResponse<ModuleImportPreviewData>(response);

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setImportPreviewState({
          status: "error",
          item: null,
          message: responseBody.message || `Excel取込プレビューに失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setImportPreviewState({
        status: "success",
        item: responseBody.data,
        message: responseBody.message || "Excel入力を正規化しました。",
      });
    } catch (error) {
      setImportPreviewState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : "Excel取込プレビューに失敗しました。",
      });
    }
  }

  const createdItem = createState.item;
  const previewItem = importPreviewState.item;

  return (
    <Page
      title="モジュール登録"
      description="装置ブロックと手順行を入力して初版モジュールを保存します。装置は横方向に最大20台まで追加できます。"
    >
      <section className="upload-zone" aria-label="モジュール登録ガイダンス">
        <span className="upload-icon">+</span>
        <h2>先に装置ブロックを追加し、そのあと手順行を追加します</h2>
        <p>装置ごとに「時刻 / target / P / 対象装置」と、各手順行に対する「時刻 / window / P / コマンド」をまとめて入力できます。</p>
      </section>

      {isNewVersionMode ? (
        <section className="register-status register-status-success">
          <span>新しい版をExcelから作成</span>
          <strong>{versionSourceModuleKey}</strong>
          <p>
            {`対象: ${versionSourceModuleKey} / ${versionSourceModuleName ?? "名称未指定"}。作成予定: 次のdraft版。`}
          </p>
          <div className="register-result-meta">
            <span>{`module_id: ${versionSourceModuleId ?? "-"}`}</span>
            <span>{`module_key: ${versionSourceModuleKey}`}</span>
            <span>{`internal version_no: ${versionNextVersion ?? "-"}`}</span>
          </div>
        </section>
      ) : null}

      <form className="register-form" onSubmit={handleSubmit}>
        {/*
          MVPではモジュール登録をExcel投入のみに寄せるため、手入力用の基本情報フォームは表示しない。
          値はExcel取込結果から内部状態へ反映し、保存リクエストでは引き続き使用する。
        */}

        <section className="register-step-card">
          <div className="register-step-header">
            <div>
              <h2>装置ブロック</h2>
              <p className="register-section-copy">
                装置を横方向に追加できます。各装置ブロックの中に
                「時刻 / target / P / 対象装置」と、
                各手順行の「時刻 / window / P / コマンド」をまとめて持ちます。
              </p>
            </div>
            <button className="secondary" type="button" onClick={addDeviceSlot} disabled={deviceHeaders.length >= 20}>
              <span aria-hidden="true">+</span>
              装置追加
            </button>
          </div>
          <div className="register-device-accordion-list">
            {deviceHeaders.map((header) => (
              <details key={header.slotNo} className="register-device-accordion" open={header.slotNo === 1}>
                <summary className="register-device-accordion-summary">
                  <div className="register-device-accordion-title">
                    <strong>{`装置 ${header.slotNo}`}</strong>
                    <span>{header.targetDeviceText || "装置名未入力"}</span>
                  </div>
                  <button
                    className="text-button"
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      removeDeviceSlot(header.slotNo);
                    }}
                    disabled={deviceHeaders.length === 1}
                  >
                    <span aria-hidden="true">-</span>
                    装置削除
                  </button>
                </summary>

                <div className="register-device-accordion-body">
                  <section className="register-device-subsection">
                    <div className="register-device-subsection-header">
                      <strong>装置基本情報</strong>
                      <span>時刻 / target / P / 対象装置</span>
                    </div>
                    <div className="register-device-header-grid">
                      <label>
                        時刻
                        <input
                          value={header.headerTimeText}
                          onChange={(event) => updateDeviceHeader(header.slotNo, "headerTimeText", event.target.value)}
                        />
                      </label>
                      <label>
                        target
                        <input
                          value={header.targetText}
                          onChange={(event) => updateDeviceHeader(header.slotNo, "targetText", event.target.value)}
                        />
                      </label>
                      <label>
                        P
                        <input value={header.pText} onChange={(event) => updateDeviceHeader(header.slotNo, "pText", event.target.value)} />
                      </label>
                      <label>
                        対象装置
                        <input
                          value={header.targetDeviceText}
                          onChange={(event) => updateDeviceHeader(header.slotNo, "targetDeviceText", event.target.value)}
                        />
                      </label>
                    </div>
                  </section>

                  <section className="register-device-subsection">
                    <div className="register-device-subsection-header">
                      <strong>手順行ごとの装置コマンド</strong>
                      <span>各手順行に対する 時刻 / window / P / コマンド</span>
                    </div>
                    <div className="register-device-command-list">
                      {rows.map((row, index) => {
                        const entry = getRegisterRowDeviceEntry(row, header.slotNo);

                        return (
                          <section key={`${header.slotNo}-${row.rowId}`} className="register-device-command-card">
                            <div className="register-device-command-card-header">
                              <strong>{`行 ${index + 1}`}</strong>
                              <span>{row.workText.trim() || "作業内容未入力"}</span>
                            </div>
                            <div className="register-device-row-group-grid">
                              <label>
                                時刻
                                <input
                                  value={entry.timeText}
                                  onChange={(event) =>
                                    updateRowDeviceEntry(row.rowId, header.slotNo, "timeText", event.target.value)
                                  }
                                />
                              </label>
                              <label>
                                window
                                <input
                                  value={entry.windowText}
                                  onChange={(event) =>
                                    updateRowDeviceEntry(row.rowId, header.slotNo, "windowText", event.target.value)
                                  }
                                />
                              </label>
                              <label>
                                P
                                <input
                                  value={entry.pText}
                                  onChange={(event) => updateRowDeviceEntry(row.rowId, header.slotNo, "pText", event.target.value)}
                                />
                              </label>
                              <label>
                                コマンド
                                <input
                                  value={entry.commandText}
                                  onChange={(event) =>
                                    updateRowDeviceEntry(row.rowId, header.slotNo, "commandText", event.target.value)
                                  }
                                />
                              </label>
                            </div>
                          </section>
                        );
                      })}
                    </div>
                  </section>
                </div>
              </details>
            ))}
          </div>
        </section>

        <section className="register-step-card">
          <div className="register-step-header">
            <div>
              <h2>手順行</h2>
              <p className="register-section-copy">
                ここでは共通の手順項目を入力します。装置ごとのコマンド欄は上の装置ブロック内で編集します。
              </p>
            </div>
            <button className="secondary" type="button" onClick={addRow}>
              <span aria-hidden="true">+</span>
              行追加
            </button>
          </div>
          <div className="register-rows">
            {rows.map((row, index) => (
              <section key={row.rowId} className="register-row-editor">
                <div className="register-row-editor-header">
                  <strong>{`行 ${index + 1}`}</strong>
                  <button className="text-button" type="button" onClick={() => removeRow(row.rowId)} disabled={rows.length === 1}>
                    <span aria-hidden="true">-</span>
                    行削除
                  </button>
                </div>
                <div className="register-row-grid">
                  <label>
                    段落
                    <select value={row.indentLevel} onChange={(event) => updateRow(row.rowId, "indentLevel", Number(event.target.value))}>
                      <option value={0}>1段</option>
                      <option value={1}>2段</option>
                      <option value={2}>3段</option>
                      <option value={3}>4段</option>
                    </select>
                  </label>
                  <label>
                    大
                    <input value={row.majorNo} onChange={(event) => updateRow(row.rowId, "majorNo", event.target.value)} />
                  </label>
                  <label>
                    中
                    <input value={row.middleNo} onChange={(event) => updateRow(row.rowId, "middleNo", event.target.value)} />
                  </label>
                  <label>
                    小
                    <input value={row.minorNo} onChange={(event) => updateRow(row.rowId, "minorNo", event.target.value)} />
                  </label>
                  <label>
                    技術資料名
                    <input value={row.techDocText} onChange={(event) => updateRow(row.rowId, "techDocText", event.target.value)} />
                  </label>
                  <label className="wide">
                    作業内容
                    <textarea
                      className={`register-work-indent-${row.indentLevel}`}
                      value={row.workText}
                      onChange={(event) => updateRow(row.rowId, "workText", event.target.value)}
                      required
                    />
                  </label>
                  <label className="wide">
                    確認事項 / 項目
                    <input value={row.expectedResult} onChange={(event) => updateRow(row.rowId, "expectedResult", event.target.value)} />
                  </label>
                </div>
              </section>
            ))}
          </div>
        </section>

        <section className="register-step-card">
          <div className="register-step-header">
            <div>
              <h2>Excel取込プレビュー</h2>
              <p className="register-section-copy">
                現在の入力を 1 シート相当の JSON として <code>POST /api/v1/modules/import-sheet</code> に送り、
                正規化後の内容を確認します。
              </p>
            </div>
            <button className="secondary" type="button" onClick={() => void handleImportPreview()}>
              <span aria-hidden="true">⇄</span>
              プレビュー実行
            </button>
          </div>

          <section
            className={`register-status ${
              importPreviewState.status === "success"
                ? "register-status-success"
                : importPreviewState.status === "error"
                  ? "register-status-error"
                  : importPreviewState.status === "submitting"
                    ? "register-status-submitting"
                    : ""
            }`}
          >
            <span>プレビュー状態</span>
            <strong>
              {importPreviewState.status === "success"
                ? "正規化完了"
                : importPreviewState.status === "error"
                  ? "変換失敗"
                  : importPreviewState.status === "submitting"
                    ? "変換中"
                    : "未実行"}
            </strong>
            <p>{importPreviewState.message}</p>
            {previewItem ? (
              <>
                <div className="register-result-meta">
                  <span>{previewItem.module_key ?? "自動採番"}</span>
                  <span>{previewItem.module_name}</span>
                  <span>{`装置 ${previewItem.device_headers.length} 台`}</span>
                  <span>{`手順行 ${previewItem.rows.length} 行`}</span>
                </div>
                <details className="json-preview-wrap">
                  <summary>正規化結果を表示</summary>
                  <pre className="json-preview">{JSON.stringify(previewItem, null, 2)}</pre>
                </details>
              </>
            ) : null}
          </section>
        </section>

        <section
          className={`register-status ${
            createState.status === "success"
              ? "register-status-success"
              : createState.status === "error"
                ? "register-status-error"
                : createState.status === "submitting"
                  ? "register-status-submitting"
                  : ""
          }`}
        >
          <span>保存状態</span>
          <strong>
            {createState.status === "success"
              ? "保存完了"
              : createState.status === "error"
                ? "保存失敗"
                : createState.status === "submitting"
                  ? "保存中"
                  : "入力待ち"}
          </strong>
          <p>{createState.message}</p>
          {createdItem ? (
            <div className="register-result-meta">
              <span>{createdItem.module_key}</span>
              <span>{`版 ${formatVersionLabel(createdItem)}`}</span>
              <span>{createdItem.status_label}</span>
              <span>{`装置 ${createdItem.device_headers.length} 台`}</span>
            </div>
          ) : null}
        </section>

        <Toolbar>
          {createdItem ? (
            <button className="secondary" type="button" onClick={() => navigate(`/modules/${createdItem.module_id}?version_no=${createdItem.version_no}`)}>
              <span aria-hidden="true">&lt;-</span>
              詳細を開く
            </button>
          ) : null}
          <button className="primary" type="submit" disabled={createState.status === "submitting"}>
            <span aria-hidden="true">✎</span>
            {createState.status === "submitting" ? "保存中..." : "保存実行"}
          </button>
        </Toolbar>
      </form>
    </Page>
  );
}

function ModuleRegisterPageV2() {
  type RegisterRowType = "header" | "step" | "meta" | "spacer";
  type RegisterRowDraft = {
    rowId: number;
    rowType: RegisterRowType;
    indentLevel: number;
    majorNo: string;
    middleNo: string;
    minorNo: string;
    techDocText: string;
    workText: string;
    expectedResult: string;
    deviceEntries: ModuleRegisterDeviceEntryDraft[];
    images: ModuleRowImageData[];
  };

  const navigate = useNavigate();
  const currentUser = getStoredAuthUser();
  const isAdmin = currentUser?.role === "admin";
  const [searchParams] = useSearchParams();
  const versionSourceModuleId = searchParams.get("module_id");
  const versionSourceModuleKey = searchParams.get("module_key");
  const versionSourceModuleName = searchParams.get("module_name");
  const versionNextVersion = searchParams.get("next_version");
  const isNewVersionMode = searchParams.get("mode") === "new-version" && versionSourceModuleKey !== null;
  const [moduleKeyInput, setModuleKeyInput] = useState("");
  const [moduleNameInput, setModuleNameInput] = useState("初期点検手順");
  const [descriptionInput, setDescriptionInput] = useState("モジュール登録画面から作成。");
  const [sourcePathInput, setSourcePathInput] = useState("imports/manual-module.xlsx");
  const [createdByInput, setCreatedByInput] = useState("webui");
  const [selectedImportFile, setSelectedImportFile] = useState<File | null>(null);
  const [deviceHeaders, setDeviceHeaders] = useState<ModuleRegisterDeviceHeaderDraft[]>([
    {
      slotNo: 1,
      headerTimeText: "09:00",
      targetText: "CS",
      pText: ">",
      targetDeviceText: "device-01",
    },
  ]);
  const [rowSeed, setRowSeed] = useState(2);
  const [rows, setRows] = useState<RegisterRowDraft[]>([
    {
      rowId: 1,
      rowType: "step",
      indentLevel: 0,
      majorNo: "1",
      middleNo: "1",
      minorNo: "1",
      techDocText: "技術資料",
      workText: "作業前確認。",
      expectedResult: "準備完了。",
      deviceEntries: [
        {
          slotNo: 1,
          timeText: "5分",
          windowText: "コンソール",
          pText: ">",
          commandText: "show version",
        },
      ],
      images: [],
    },
  ]);
  const [createState, setCreateState] = useState<ModuleCreateState>({
    status: "idle",
    item: null,
    message: "Excelファイルを取り込んでから、初版モジュールを保存してください。",
  });
  const [importPreviewState, setImportPreviewState] = useState<ModuleImportPreviewState>({
    status: "idle",
    item: null,
    message: isAdmin
      ? "Excel取込プレビューはまだ実行していません。"
      : "Excelファイルはまだ取り込まれていません。",
  });
  const [similarityState, setSimilarityState] = useState<ModuleSimilarityCheckState>({
    status: "idle",
    item: null,
    message: "Excel取込後に類似モジュールを確認します。",
  });
  const [similarityRegistrationConfirmed, setSimilarityRegistrationConfirmed] = useState(false);
  const [similarityDiffState, setSimilarityDiffState] = useState<ModuleDiffState>({
    status: "idle",
    item: null,
    message: "候補を選ぶと取込内容との差分を確認できます。",
  });
  const [similarityDiffCandidate, setSimilarityDiffCandidate] = useState<ModuleSimilarityCandidateData | null>(null);
  const [similarityDiffDownloadState, setSimilarityDiffDownloadState] = useState<ModuleSimilarityDiffDownloadState>({
    status: "idle",
    candidateId: null,
    message: "",
  });
  const [importFileInputKey, setImportFileInputKey] = useState(0);
  const [isWorkbookImportApplied, setIsWorkbookImportApplied] = useState(false);
  const [isImportPreviewFullscreenOpen, setIsImportPreviewFullscreenOpen] = useState(false);
  const hasSimilarityCandidates = (similarityState.item?.candidate_count ?? 0) > 0;
  const canSaveImportedModule =
    (isWorkbookImportApplied || importPreviewState.status === "success")
    && similarityState.status === "success"
    && (!hasSimilarityCandidates || similarityRegistrationConfirmed);

  useEffect(() => {
    if (!isNewVersionMode || versionSourceModuleKey === null) {
      return;
    }
    setModuleKeyInput(versionSourceModuleKey);
    if (versionSourceModuleName !== null) {
      setModuleNameInput(versionSourceModuleName);
    }
    setCreateState((current) => ({
      ...current,
      message: `${versionSourceModuleKey} の新しい版をExcelから作成します。`,
    }));
  }, [isNewVersionMode, versionSourceModuleKey, versionSourceModuleName]);

  useEffect(() => {
    if (!importPreviewState.item) {
      setIsImportPreviewFullscreenOpen(false);
    }
  }, [importPreviewState.item]);

  function blankDeviceEntry(slotNo: number): ModuleRegisterDeviceEntryDraft {
    return {
      slotNo,
      timeText: "",
      windowText: "",
      pText: "",
      commandText: "",
    };
  }

  function normalizeRowType(value: string): RegisterRowType {
    if (value === "header" || value === "meta" || value === "spacer") {
      return value;
    }
    return "step";
  }

  function createDefaultRow(rowId: number): RegisterRowDraft {
    return {
      rowId,
      rowType: "step",
      indentLevel: 0,
      majorNo: "",
      middleNo: "",
      minorNo: "",
      techDocText: "",
      workText: "",
      expectedResult: "",
      deviceEntries: deviceHeaders.map((header) => blankDeviceEntry(header.slotNo)),
      images: [],
    };
  }

  function getRegisterRowDeviceEntry(row: RegisterRowDraft, slotNo: number): ModuleRegisterDeviceEntryDraft {
    return row.deviceEntries.find((candidate) => candidate.slotNo === slotNo) ?? blankDeviceEntry(slotNo);
  }

  function updateRow(rowId: number, field: keyof RegisterRowDraft, value: string | number): void {
    setRows((currentRows) => currentRows.map((row) => (row.rowId === rowId ? { ...row, [field]: value } : row)));
  }

  function updateDeviceHeader(
    slotNo: number,
    field: keyof Omit<ModuleRegisterDeviceHeaderDraft, "slotNo">,
    value: string,
  ): void {
    setDeviceHeaders((currentHeaders) =>
      currentHeaders.map((header) => (header.slotNo === slotNo ? { ...header, [field]: value } : header)),
    );
  }

  function updateRowDeviceEntry(
    rowId: number,
    slotNo: number,
    field: keyof Omit<ModuleRegisterDeviceEntryDraft, "slotNo">,
    value: string,
  ): void {
    setRows((currentRows) =>
      currentRows.map((row) =>
        row.rowId === rowId
          ? {
              ...row,
              deviceEntries: row.deviceEntries.map((entry) =>
                entry.slotNo === slotNo ? { ...entry, [field]: value } : entry,
              ),
            }
          : row,
      ),
    );
  }

  function addDeviceSlot(): void {
    setDeviceHeaders((currentHeaders) => {
      if (currentHeaders.length >= 20) {
        return currentHeaders;
      }

      const nextSlotNo = Math.max(...currentHeaders.map((header) => header.slotNo)) + 1;
      setRows((currentRows) =>
        currentRows.map((row) => ({
          ...row,
          deviceEntries: [...row.deviceEntries, blankDeviceEntry(nextSlotNo)],
        })),
      );

      return [
        ...currentHeaders,
        {
          slotNo: nextSlotNo,
          headerTimeText: "",
          targetText: "",
          pText: "",
          targetDeviceText: `device-${String(nextSlotNo).padStart(2, "0")}`,
        },
      ];
    });
  }

  function removeDeviceSlot(slotNo: number): void {
    setDeviceHeaders((currentHeaders) => {
      if (currentHeaders.length === 1) {
        return currentHeaders;
      }

      setRows((currentRows) =>
        currentRows.map((row) => ({
          ...row,
          deviceEntries: row.deviceEntries.filter((entry) => entry.slotNo !== slotNo),
        })),
      );

      return currentHeaders.filter((header) => header.slotNo !== slotNo);
    });
  }

  function addRow(): void {
    setRows((currentRows) => [...currentRows, createDefaultRow(rowSeed)]);
    setRowSeed((currentSeed) => currentSeed + 1);
  }

  function removeRow(rowId: number): void {
    setRows((currentRows) => (currentRows.length > 1 ? currentRows.filter((row) => row.rowId !== rowId) : currentRows));
  }

  function buildCurrentModulePayload(): ModuleImportPreviewData {
    const firstHeader = deviceHeaders[0] ?? null;
    return {
      module_key: moduleKeyInput.trim() || null,
      module_name: moduleNameInput.trim(),
      description: descriptionInput.trim() || null,
      change_note: importPreviewState.item?.change_note ?? null,
      source_xlsx_path: sourcePathInput.trim() || null,
      source_sha256: importPreviewState.item?.source_sha256 ?? null,
      created_by: createdByInput.trim() || null,
      header_time_text: firstHeader?.headerTimeText.trim() || null,
      target_text: firstHeader?.targetText.trim() || null,
      common_p_text: firstHeader?.pText.trim() || null,
      target_device_text: firstHeader?.targetDeviceText.trim() || null,
      device_headers: deviceHeaders.map((header) => ({
        slot_no: header.slotNo,
        header_time_text: header.headerTimeText.trim() || null,
        target_text: header.targetText.trim() || null,
        p_text: header.pText.trim() || null,
        target_device_text: header.targetDeviceText.trim() || null,
      })),
      rows: rows.map((row, index) => {
        const firstEntry = row.deviceEntries[0] ?? null;
        return {
          row_order: index + 1,
          row_type: row.rowType,
          major_no: row.majorNo.trim() || null,
          middle_no: row.middleNo.trim() || null,
          minor_no: row.minorNo.trim() || null,
          tech_doc_text: row.techDocText.trim() || null,
          work_text: row.workText.trim() || null,
          indent_level: row.indentLevel,
          expected_result: row.expectedResult.trim() || null,
          time_text: firstEntry?.timeText.trim() || null,
          window_text: firstEntry?.windowText.trim() || null,
          p_text: firstEntry?.pText.trim() || null,
          command_text: firstEntry?.commandText.trim() || null,
          note: null,
          images: row.images ?? [],
          device_entries: row.deviceEntries.map((entry) => ({
            slot_no: entry.slotNo,
            time_text: entry.timeText.trim() || null,
            window_text: entry.windowText.trim() || null,
            p_text: entry.pText.trim() || null,
            command_text: entry.commandText.trim() || null,
          })),
        };
      }),
    };
  }

  function resetSimilarityReview(message = "Excel取込後に類似モジュールを確認します。"): void {
    setSimilarityState({
      status: "idle",
      item: null,
      message,
    });
    setSimilarityRegistrationConfirmed(false);
    setSimilarityDiffCandidate(null);
    setSimilarityDiffState({
      status: "idle",
      item: null,
      message: "候補を選ぶと取込内容との差分を確認できます。",
    });
    setSimilarityDiffDownloadState({
      status: "idle",
      candidateId: null,
      message: "",
    });
  }

  async function runSimilarityCheck(payload: ModuleImportPreviewData): Promise<void> {
    setSimilarityState({
      status: "submitting",
      item: null,
      message: "承認済みモジュールとの類似度を確認しています...",
    });
    setSimilarityRegistrationConfirmed(false);
    setSimilarityDiffCandidate(null);
    setSimilarityDiffState({
      status: "idle",
      item: null,
      message: "候補を選ぶと取込内容との差分を確認できます。",
    });
    setSimilarityDiffDownloadState({
      status: "idle",
      candidateId: null,
      message: "",
    });

    try {
      const response = await fetch(buildApiUrl("/api/v1/modules/similarity-check"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const responseBody = await readApiResponse<ModuleSimilarityCheckData>(response);
      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setSimilarityState({
          status: "error",
          item: null,
          message: responseBody.message || `類似モジュール確認に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setSimilarityState({
        status: "success",
        item: responseBody.data,
        message:
          responseBody.data.candidate_count > 0
            ? `${responseBody.data.candidate_count} 件の類似候補が見つかりました。差分を確認して登録可否を判断してください。`
            : "類似候補は見つかりませんでした。登録へ進めます。",
      });
    } catch (error) {
      setSimilarityState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : "類似モジュール確認に失敗しました。",
      });
    }
  }

  async function handleSimilarityDiff(candidate: ModuleSimilarityCandidateData): Promise<void> {
    setSimilarityDiffCandidate(candidate);
    setSimilarityDiffState({
      status: "loading",
      item: null,
      message: `${candidate.module_key} との差分を取得しています...`,
    });

    try {
      const query = new URLSearchParams({ version_no: String(candidate.version_no) });
      const response = await fetch(
        buildApiUrl(`/api/v1/modules/${candidate.module_id}/diff-preview?${query.toString()}`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(buildCurrentModulePayload()),
        },
      );
      const responseBody = await readApiResponse<ModuleDiffData>(response);
      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setSimilarityDiffState({
          status: "unavailable",
          item: null,
          message: responseBody.message || `差分取得に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setSimilarityDiffState({
        status: "available",
        item: responseBody.data,
        message: responseBody.message || "取込内容との差分を取得しました。",
      });
    } catch (error) {
      setSimilarityDiffState({
        status: "unavailable",
        item: null,
        message: error instanceof Error ? error.message : "差分取得に失敗しました。",
      });
    }
  }

  async function handleSimilarityDiffDownload(
    candidate: ModuleSimilarityCandidateData,
  ): Promise<void> {
    if (!selectedImportFile) {
      setSimilarityDiffDownloadState({
        status: "error",
        candidateId: candidate.module_version_id,
        message: "比較対象のExcelファイルを選択してください。",
      });
      return;
    }

    setSimilarityDiffDownloadState({
      status: "loading",
      candidateId: candidate.module_version_id,
      message: `${candidate.module_key} との差分Excelを作成しています...`,
    });

    try {
      const query = new URLSearchParams({
        version_no: String(candidate.version_no),
        filename: selectedImportFile.name,
      });
      if (createdByInput.trim()) {
        query.set("created_by", createdByInput.trim());
      }
      const response = await fetch(
        buildApiUrl(`/api/v1/modules/${candidate.module_id}/diff-preview/download?${query.toString()}`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/octet-stream",
          },
          body: await selectedImportFile.arrayBuffer(),
        },
      );

      if (!response.ok) {
        const responseBody = await readApiResponse<unknown>(response);
        setSimilarityDiffDownloadState({
          status: "error",
          candidateId: candidate.module_version_id,
          message: responseBody.message || `差分Excelの作成に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get("Content-Disposition") ?? "";
      const encodedFilename = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
      const plainFilename = contentDisposition.match(/filename="?([^";]+)"?/i)?.[1];
      const filename = encodedFilename
        ? decodeURIComponent(encodedFilename)
        : plainFilename ?? `module-diff-${candidate.module_key}-v${candidate.version_no}-import.xlsx`;
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
      setSimilarityDiffDownloadState({
        status: "success",
        candidateId: candidate.module_version_id,
        message: `${filename} をダウンロードしました。比較元・比較先の淡い紫色のセルが差分です。`,
      });
    } catch (error) {
      setSimilarityDiffDownloadState({
        status: "error",
        candidateId: candidate.module_version_id,
        message: error instanceof Error ? error.message : "差分Excelの作成に失敗しました。",
      });
    }
  }

  function handleCancelSimilarityRegistration(): void {
    setSelectedImportFile(null);
    setImportFileInputKey((current) => current + 1);
    setIsWorkbookImportApplied(false);
    setImportPreviewState({
      status: "idle",
      item: null,
      message: "登録を中止しました。別のExcelファイルを選択できます。",
    });
    resetSimilarityReview("登録を中止しました。Excel取込後に再度確認します。");
    setCreateState({
      status: "idle",
      item: null,
      message: "登録を中止しました。",
    });
  }

  function applyImportedDraft(item: ModuleImportPreviewData): void {
    const nextHeaders =
      item.device_headers.length > 0
        ? item.device_headers.map((header) => ({
            slotNo: header.slot_no,
            headerTimeText: header.header_time_text ?? "",
            targetText: header.target_text ?? "",
            pText: header.p_text ?? "",
            targetDeviceText: header.target_device_text ?? `device-${String(header.slot_no).padStart(2, "0")}`,
          }))
        : [
            {
              slotNo: 1,
              headerTimeText: item.header_time_text ?? "",
              targetText: item.target_text ?? "",
              pText: item.common_p_text ?? "",
              targetDeviceText: item.target_device_text ?? "device-01",
            },
          ];

    const nextRows =
      item.rows.length > 0
        ? item.rows.map((row, index) => ({
            rowId: index + 1,
            rowType: normalizeRowType(row.row_type),
            indentLevel: row.indent_level ?? 0,
            majorNo: row.major_no ?? "",
            middleNo: row.middle_no ?? "",
            minorNo: row.minor_no ?? "",
            techDocText: row.tech_doc_text ?? "",
            workText: row.work_text ?? "",
            expectedResult: row.expected_result ?? "",
            images: row.images ?? [],
            deviceEntries: nextHeaders.map((header) => {
              const entry = row.device_entries.find((candidate) => candidate.slot_no === header.slotNo);
              return {
                slotNo: header.slotNo,
                timeText: entry?.time_text ?? "",
                windowText: entry?.window_text ?? "",
                pText: entry?.p_text ?? "",
                commandText: entry?.command_text ?? "",
              };
            }),
          }))
        : [createDefaultRow(1)];

    setModuleKeyInput(isNewVersionMode && versionSourceModuleKey !== null ? versionSourceModuleKey : (item.module_key ?? ""));
    setModuleNameInput(item.module_name);
    setDescriptionInput(item.description ?? "");
    setSourcePathInput(item.source_xlsx_path ?? "");
    setCreatedByInput(item.created_by ?? "webui");
    setDeviceHeaders(nextHeaders);
    setRows(nextRows);
    setRowSeed(nextRows.length + 1);
    setCreateState({
      status: "idle",
      item: null,
      message: "取込結果を画面へ反映しました。必要に応じて修正してから保存してください。",
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    if (similarityState.status !== "success") {
      setCreateState({
        status: "error",
        item: null,
        message: "類似モジュール確認が完了していません。Excelファイルを取り込み直してください。",
      });
      return;
    }

    if (hasSimilarityCandidates && !similarityRegistrationConfirmed) {
      setCreateState({
        status: "error",
        item: null,
        message: "類似候補を確認し、「登録を続ける」を選択してください。",
      });
      return;
    }

    if (
      hasSimilarityCandidates
      && similarityRegistrationConfirmed
      && !similarityState.item?.confirmation_token
    ) {
      setCreateState({
        status: "error",
        item: null,
        message: "確認情報を取得できませんでした。Excelファイルを取り込み直してください。",
      });
      return;
    }

    if (!canSaveImportedModule) {
      setCreateState({
        status: "error",
        item: null,
        message: "先にExcelファイル取込を実行してください。",
      });
      return;
    }

    setCreateState({
      status: "submitting",
      item: null,
      message: "入力内容を登録しています...",
    });

    try {
      const query = new URLSearchParams();
      if (hasSimilarityCandidates && similarityState.item?.confirmation_token) {
        query.set(
          "similarity_confirmation_token",
          similarityState.item.confirmation_token,
        );
      }
      const createPath = query.size > 0
        ? `/api/v1/modules?${query.toString()}`
        : "/api/v1/modules";
      const response = await fetch(buildApiUrl(createPath), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildCurrentModulePayload()),
      });

      const responseBody = await readApiResponse<
        ModuleDetailData | ModuleSimilarityCheckData
      >(response);
      if (
        response.status === 409
        && responseBody.data !== null
        && "candidate_count" in responseBody.data
      ) {
        setSimilarityState({
          status: "success",
          item: responseBody.data,
          message:
            responseBody.message
            || "類似候補が更新されました。内容を再確認してください。",
        });
        setSimilarityRegistrationConfirmed(false);
        setSimilarityDiffCandidate(null);
        setSimilarityDiffState({
          status: "idle",
          item: null,
          message: "候補を選ぶと行単位の差分を確認できます。",
        });
        setSimilarityDiffDownloadState({
          status: "idle",
          candidateId: null,
          message: "",
        });
        setCreateState({
          status: "error",
          item: null,
          message:
            responseBody.message
            || "類似候補が更新されました。内容を再確認してください。",
        });
        return;
      }

      if (
        !response.ok
        || responseBody.result !== "success"
        || responseBody.data === null
        || !("module_id" in responseBody.data)
      ) {
        setCreateState({
          status: "error",
          item: null,
          message: responseBody.message || `モジュール登録に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setCreateState({
        status: "success",
        item: responseBody.data,
        message: responseBody.message || "モジュールを登録しました。",
      });
      setModuleKeyInput(responseBody.data.module_key);
    } catch (error) {
      setCreateState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : "モジュール登録に失敗しました。",
      });
    }
  }

  async function handleWorkbookImport(): Promise<void> {
    if (!selectedImportFile) {
      setImportPreviewState({
        status: "error",
        item: null,
        message: "先に xlsx / xlsm ファイルを選択してください。",
      });
      return;
    }

    setImportPreviewState({
      status: "submitting",
      item: null,
      message: "ワークブックを取り込んでいます...",
    });

    try {
      const query = new URLSearchParams({ filename: selectedImportFile.name });
      if (createdByInput.trim()) {
        query.set("created_by", createdByInput.trim());
      }

      const response = await fetch(`${buildApiUrl("/api/v1/modules/import")}?${query.toString()}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/octet-stream",
        },
        body: await selectedImportFile.arrayBuffer(),
      });

      const responseBody = await readApiResponse<ModuleImportPreviewData>(response);
      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setImportPreviewState({
          status: "error",
          item: null,
          message: responseBody.message || `Excelファイル取込に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      const importedDraft =
        isNewVersionMode && versionSourceModuleKey !== null
          ? { ...responseBody.data, module_key: versionSourceModuleKey }
          : responseBody.data;
      applyImportedDraft(importedDraft);
      setIsWorkbookImportApplied(true);
      setImportPreviewState({
        status: "success",
        item: importedDraft,
        message: responseBody.message || "ワークブック取込結果を画面へ反映しました。",
      });
      await runSimilarityCheck(importedDraft);
    } catch (error) {
      setImportPreviewState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : "Excelファイル取込に失敗しました。",
      });
    }
  }

  async function handleImportPreview(): Promise<void> {
    setImportPreviewState({
      status: "submitting",
      item: null,
      message: "Excel取込プレビューを変換しています...",
    });

    try {
      const response = await fetch(buildApiUrl("/api/v1/modules/import-sheet"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          module_key: moduleKeyInput.trim() || undefined,
          module_name: moduleNameInput.trim(),
          description: descriptionInput.trim() || undefined,
          change_note: "登録画面からプレビュー",
          source_xlsx_path: sourcePathInput.trim() || undefined,
          created_by: createdByInput.trim() || undefined,
          device_header_cells: deviceHeaders.map((header) => ({
            slot_no: header.slotNo,
            header_time_text: header.headerTimeText.trim() || undefined,
            target_text: header.targetText.trim() || undefined,
            p_text: header.pText.trim() || undefined,
            target_device_text: header.targetDeviceText.trim() || undefined,
          })),
          row_cells: rows.map((row) => {
            const payload: Record<string, unknown> = {
              A: row.majorNo.trim() || undefined,
              B: row.middleNo.trim() || undefined,
              C: row.minorNo.trim() || undefined,
              D: row.techDocText.trim() || undefined,
              I: row.expectedResult.trim() || undefined,
              device_entries: row.deviceEntries.map((entry) => ({
                slot_no: entry.slotNo,
                time_text: entry.timeText.trim() || undefined,
                window_text: entry.windowText.trim() || undefined,
                p_text: entry.pText.trim() || undefined,
                command_text: entry.commandText.trim() || undefined,
              })),
            };
            payload[(["E", "F", "G", "H"][row.indentLevel] ?? "E")] = row.workText.trim() || undefined;
            return payload;
          }),
        }),
      });

      const responseBody = await readApiResponse<ModuleImportPreviewData>(response);
      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setImportPreviewState({
          status: "error",
          item: null,
          message: responseBody.message || `Excel取込プレビューに失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setImportPreviewState({
        status: "success",
        item: responseBody.data,
        message: responseBody.message || "Excel取込プレビューを正規化しました。",
      });
      await runSimilarityCheck(responseBody.data);
    } catch (error) {
      setImportPreviewState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : "Excel取込プレビューに失敗しました。",
      });
    }
  }

  const createdItem = createState.item;
  const previewItem = importPreviewState.item;
  const previewModuleItem = previewItem ? convertImportPreviewToModuleDetail(previewItem) : null;
  const showManualEditors = false;

  return (
    <Page
      title="モジュール登録"
      description="Excelファイルを取り込み、内容を確認してから初版モジュールを保存します。"
    >
      {/* MVPではExcel投入のみでモジュール登録するため、装飾用の案内画像/アップロード枠は表示しない。 */}

      <form className="register-form" onSubmit={handleSubmit}>
        {/*
          MVPではモジュール登録をExcel投入のみに寄せるため、手入力用の基本情報フォームは表示しない。
          値はExcel取込結果から内部状態へ反映し、保存リクエストでは引き続き使用する。
        */}

        {/* Excel取込のみで登録する方針のため、手入力用の装置ブロックと手順行はWebUIでは表示しません。 */}
        {isNewVersionMode ? (
          <section className="register-status register-status-success">
            <span>新しい版をExcelから作成</span>
            <strong>{versionSourceModuleKey}</strong>
            <p>
              {`対象: ${versionSourceModuleKey} / ${versionSourceModuleName ?? "名称未指定"}。作成予定: 次のdraft版。`}
            </p>
            <div className="register-result-meta">
              <span>{`module_id: ${versionSourceModuleId ?? "-"}`}</span>
              <span>{`module_key: ${versionSourceModuleKey}`}</span>
              <span>{`internal version_no: ${versionNextVersion ?? "-"}`}</span>
            </div>
          </section>
        ) : null}

        {showManualEditors ? (
          <>
        <details className="register-panel-accordion" open>
          <summary className="register-panel-summary">
            <div>
              <h2>装置ブロック</h2>
              <p className="register-section-copy">
                装置を横方向に追加できます。各装置ブロックの中に「時刻 / target / P / 対象装置」と、各手順行の「時刻 / window / P / コマンド」をまとめて持ちます。
              </p>
            </div>
            <div className="register-panel-summary-actions">
              <span className="register-panel-toggle-indicator" aria-hidden="true">
                開閉
              </span>
              <button
                className="secondary"
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  addDeviceSlot();
                }}
                disabled={deviceHeaders.length >= 20}
              >
                <span aria-hidden="true">+</span>
                装置追加
              </button>
            </div>
          </summary>
          <div className="register-panel-body">
            <div className="register-device-accordion-list">
            {deviceHeaders.map((header) => (
              <details key={header.slotNo} className="register-device-accordion" open={header.slotNo === 1}>
                <summary className="register-device-accordion-summary">
                  <div className="register-device-accordion-title">
                    <strong>{`装置 ${header.slotNo}`}</strong>
                    <span>{header.targetDeviceText || "装置名未入力"}</span>
                  </div>
                  <button
                    className="text-button"
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      removeDeviceSlot(header.slotNo);
                    }}
                    disabled={deviceHeaders.length === 1}
                  >
                    <span aria-hidden="true">-</span>
                    装置削除
                  </button>
                </summary>

                <div className="register-device-accordion-body">
                  <section className="register-device-subsection">
                    <div className="register-device-subsection-header">
                      <strong>装置基本情報</strong>
                      <span>時刻 / target / P / 対象装置</span>
                    </div>
                    <div className="register-device-header-grid">
                      <label>
                        時刻
                        <input
                          value={header.headerTimeText}
                          onChange={(event) => updateDeviceHeader(header.slotNo, "headerTimeText", event.target.value)}
                        />
                      </label>
                      <label>
                        target
                        <input
                          value={header.targetText}
                          onChange={(event) => updateDeviceHeader(header.slotNo, "targetText", event.target.value)}
                        />
                      </label>
                      <label>
                        P
                        <input value={header.pText} onChange={(event) => updateDeviceHeader(header.slotNo, "pText", event.target.value)} />
                      </label>
                      <label>
                        対象装置
                        <input
                          value={header.targetDeviceText}
                          onChange={(event) => updateDeviceHeader(header.slotNo, "targetDeviceText", event.target.value)}
                        />
                      </label>
                    </div>
                  </section>

                  <section className="register-device-subsection">
                    <div className="register-device-subsection-header">
                      <strong>手順行ごとの装置コマンド</strong>
                      <span>各手順行に対する 時刻 / window / P / コマンド</span>
                    </div>
                    <div className="register-device-command-list">
                      {rows.map((row, index) => {
                        const entry = getRegisterRowDeviceEntry(row, header.slotNo);
                        return (
                          <section key={`${header.slotNo}-${row.rowId}`} className="register-device-command-card">
                            <div className="register-device-command-card-header">
                              <strong>{`行 ${index + 1}`}</strong>
                              <span>{row.workText.trim() || "作業内容未入力"}</span>
                            </div>
                            <div className="register-device-row-group-grid">
                              <label>
                                時刻
                                <input
                                  value={entry.timeText}
                                  onChange={(event) => updateRowDeviceEntry(row.rowId, header.slotNo, "timeText", event.target.value)}
                                />
                              </label>
                              <label>
                                window
                                <input
                                  value={entry.windowText}
                                  onChange={(event) => updateRowDeviceEntry(row.rowId, header.slotNo, "windowText", event.target.value)}
                                />
                              </label>
                              <label>
                                P
                                <input
                                  value={entry.pText}
                                  onChange={(event) => updateRowDeviceEntry(row.rowId, header.slotNo, "pText", event.target.value)}
                                />
                              </label>
                              <label>
                                コマンド
                                <input
                                  value={entry.commandText}
                                  onChange={(event) => updateRowDeviceEntry(row.rowId, header.slotNo, "commandText", event.target.value)}
                                />
                              </label>
                            </div>
                          </section>
                        );
                      })}
                    </div>
                  </section>
                </div>
              </details>
            ))}
          </div>
          </div>
        </details>

        <details className="register-panel-accordion" open>
          <summary className="register-panel-summary">
            <div>
              <h2>手順行</h2>
              <p className="register-section-copy">
                ここでは共通の手順項目を入力します。装置ごとのコマンド列は上の装置ブロック側で編集します。
              </p>
            </div>
            <div className="register-panel-summary-actions">
              <span className="register-panel-toggle-indicator" aria-hidden="true">
                開閉
              </span>
              <button
                className="secondary"
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  addRow();
                }}
              >
                <span aria-hidden="true">+</span>
                行追加
              </button>
            </div>
          </summary>
          <div className="register-panel-body">
            <div className="register-rows">
            {rows.map((row, index) => (
              <section key={row.rowId} className="register-row-editor">
                <div className="register-row-editor-header">
                  <strong>{`行 ${index + 1}`}</strong>
                  <button className="text-button" type="button" onClick={() => removeRow(row.rowId)} disabled={rows.length === 1}>
                    <span aria-hidden="true">-</span>
                    行削除
                  </button>
                </div>
                <div className="register-row-grid">
                  <label>
                    段落
                    <select value={row.indentLevel} onChange={(event) => updateRow(row.rowId, "indentLevel", Number(event.target.value))}>
                      <option value={0}>1段</option>
                      <option value={1}>2段</option>
                      <option value={2}>3段</option>
                      <option value={3}>4段</option>
                    </select>
                  </label>
                  <label>
                    行種別
                    <select value={row.rowType} onChange={(event) => updateRow(row.rowId, "rowType", event.target.value)}>
                      <option value="step">手順</option>
                      <option value="header">見出し</option>
                      <option value="meta">メモ</option>
                      <option value="spacer">空行</option>
                    </select>
                  </label>
                  <label>
                    大
                    <input value={row.majorNo} onChange={(event) => updateRow(row.rowId, "majorNo", event.target.value)} />
                  </label>
                  <label>
                    中
                    <input value={row.middleNo} onChange={(event) => updateRow(row.rowId, "middleNo", event.target.value)} />
                  </label>
                  <label>
                    小
                    <input value={row.minorNo} onChange={(event) => updateRow(row.rowId, "minorNo", event.target.value)} />
                  </label>
                  <label>
                    技術資料名
                    <input value={row.techDocText} onChange={(event) => updateRow(row.rowId, "techDocText", event.target.value)} />
                  </label>
                  <label className="wide">
                    作業内容
                    <textarea
                      className={`register-work-indent-${row.indentLevel}`}
                      value={row.workText}
                      onChange={(event) => updateRow(row.rowId, "workText", event.target.value)}
                      required
                    />
                  </label>
                  <label className="wide">
                    確認事項 / 項目
                    <input value={row.expectedResult} onChange={(event) => updateRow(row.rowId, "expectedResult", event.target.value)} />
                  </label>
                </div>
              </section>
            ))}
          </div>
          </div>
        </details>
          </>
        ) : null}

        <section className="register-step-card">
          <div className="register-step-header">
            <div>
              <h2>Excelファイル取込</h2>
              <p className="register-section-copy">
                xlsx / xlsm を選択して <code>POST /api/v1/modules/import</code> に送り、取込結果をこの画面へ反映します。
              </p>
            </div>
            <button
              className="secondary"
              type="button"
              onClick={() => void handleWorkbookImport()}
              disabled={!selectedImportFile || importPreviewState.status === "submitting"}
            >
              <span aria-hidden="true">↑</span>
              ファイル取込
            </button>
          </div>
          <FormGrid>
            <label className="wide">
              Excelファイル
              <input
                key={importFileInputKey}
                type="file"
                accept=".xlsx,.xlsm"
                onChange={(event) => {
                  const nextFile = event.target.files?.[0] ?? null;
                  setSelectedImportFile(nextFile);
                  setIsWorkbookImportApplied(false);
                  setImportPreviewState({
                    status: "idle",
                    item: null,
                    message: nextFile
                      ? "ファイル取込を実行してください。"
                      : "先に xlsx / xlsm ファイルを選択してください。",
                  });
                  resetSimilarityReview();
                  setCreateState({
                    status: "idle",
                    item: null,
                    message: "Excelファイルを取り込んでから、初版モジュールを保存してください。",
                  });
                }}
              />
            </label>
          </FormGrid>
          <section className="register-status">
            <span>選択状態</span>
            <strong>{selectedImportFile ? "選択済み" : "未選択"}</strong>
            <p>{selectedImportFile ? `${selectedImportFile.name} を選択しています。` : "先に xlsx / xlsm ファイルを選択してください。"}</p>
          </section>
          {!isAdmin ? (
            <section
              aria-live="polite"
              className={`register-status ${
                importPreviewState.status === "success"
                  ? "register-status-success"
                  : importPreviewState.status === "error"
                    ? "register-status-error"
                    : importPreviewState.status === "submitting"
                      ? "register-status-submitting"
                      : ""
              }`}
            >
              <span>取込状態</span>
              <strong>
                {importPreviewState.status === "success"
                  ? "取込完了"
                  : importPreviewState.status === "error"
                    ? "取込失敗"
                    : importPreviewState.status === "submitting"
                      ? "取込中"
                      : selectedImportFile
                        ? "取込待ち"
                        : "未選択"}
              </strong>
              <p>{importPreviewState.message}</p>
              {importPreviewState.status === "success" && previewItem ? (
                <div className="register-result-meta">
                  <span>{previewItem.module_key ?? "自動採番"}</span>
                  <span>{previewItem.module_name}</span>
                  <span>{`装置 ${previewItem.device_headers.length} 台`}</span>
                  <span>{`手順行 ${previewItem.rows.length} 行`}</span>
                </div>
              ) : null}
            </section>
          ) : null}
        </section>

        {isAdmin ? (
          <section className="register-step-card">
            <div className="register-step-header">
              <div>
                <h2>Excel取込プレビュー</h2>
                <p className="register-section-copy">
                  現在の入力を 1 シート相当の JSON として <code>POST /api/v1/modules/import-sheet</code> に送り、正規化内容を確認します。
                </p>
              </div>
              <button className="secondary" type="button" onClick={() => void handleImportPreview()}>
                <span aria-hidden="true">→</span>
                プレビュー実行
              </button>
            </div>

            <section
              className={`register-status ${
                importPreviewState.status === "success"
                  ? "register-status-success"
                  : importPreviewState.status === "error"
                    ? "register-status-error"
                    : importPreviewState.status === "submitting"
                      ? "register-status-submitting"
                      : ""
              }`}
            >
              <span>プレビュー状態</span>
              <strong>
                {importPreviewState.status === "success"
                  ? "正規化完了"
                  : importPreviewState.status === "error"
                    ? "変換失敗"
                    : importPreviewState.status === "submitting"
                      ? "変換中"
                      : "未実行"}
              </strong>
              <p>{importPreviewState.message}</p>
              {previewItem ? (
                <>
                  <div className="register-result-meta">
                    <span>{previewItem.module_key ?? "自動採番"}</span>
                    <span>{previewItem.module_name}</span>
                    <span>{`装置 ${previewItem.device_headers.length} 台`}</span>
                    <span>{`手順行 ${previewItem.rows.length} 行`}</span>
                  </div>
                  <details className="json-preview-wrap">
                    <summary>正規化結果を表示</summary>
                    <pre className="json-preview">{JSON.stringify(previewItem, null, 2)}</pre>
                  </details>
                </>
              ) : null}
            </section>
          </section>
        ) : null}

        <section
          className={`register-status ${
            createState.status === "success"
              ? "register-status-success"
              : createState.status === "error"
                ? "register-status-error"
                : createState.status === "submitting"
                  ? "register-status-submitting"
                  : ""
          }`}
        >
          <span>保存状態</span>
          <strong>
            {createState.status === "success"
              ? "保存完了"
              : createState.status === "error"
                ? "保存失敗"
                : createState.status === "submitting"
                  ? "保存中"
                  : "入力待ち"}
          </strong>
          <p>{createState.message}</p>
          {createdItem ? (
            <div className="register-result-meta">
              <span>{createdItem.module_key}</span>
              <span>{`版 ${formatVersionLabel(createdItem)}`}</span>
              <span>{createdItem.status_label}</span>
              <span>{`装置 ${createdItem.device_headers.length} 台`}</span>
            </div>
          ) : null}
        </section>

        <ModuleSimilarityReview
          state={similarityState}
          registrationConfirmed={similarityRegistrationConfirmed}
          diffState={similarityDiffState}
          diffCandidate={similarityDiffCandidate}
          downloadState={similarityDiffDownloadState}
          onShowDiff={(candidate) => void handleSimilarityDiff(candidate)}
          onDownloadDiff={(candidate) => void handleSimilarityDiffDownload(candidate)}
          onContinue={() => setSimilarityRegistrationConfirmed(true)}
          onCancel={handleCancelSimilarityRegistration}
        />

        <Toolbar>
          {createdItem ? (
            <button className="secondary" type="button" onClick={() => navigate(`/modules/${createdItem.module_id}?version_no=${createdItem.version_no}`)}>
              <span aria-hidden="true">&lt;-</span>
              詳細を開く
            </button>
          ) : null}
          <button className="primary" type="submit" disabled={createState.status === "submitting" || !canSaveImportedModule}>
            <span aria-hidden="true">✔</span>
            {createState.status === "submitting" ? "保存中..." : "保存実行"}
          </button>
        </Toolbar>
      </form>
            {isAdmin && isImportPreviewFullscreenOpen && previewItem && previewModuleItem ? (
        <PreviewOverlay
          title="Excel取込プレビュー"
          description="現在の取込結果を保存前に全画面で確認します。Excel出力と同じ列構造で、装置が横に増えていく形で表示します。"
          onClose={() => setIsImportPreviewFullscreenOpen(false)}
          actions={
            <button className="secondary" type="button" onClick={() => window.print()}>
              <span aria-hidden="true">P</span>
              印刷
            </button>
          }
        >
          <section className={`list-status list-status-${importPreviewState.status}`} aria-live="polite">
            <div>
              <span>プレビュー状態</span>
              <strong>
                {importPreviewState.status === "success"
                  ? "正規化完了"
                  : importPreviewState.status === "error"
                    ? "変換失敗"
                    : importPreviewState.status === "submitting"
                      ? "変換中"
                      : "未実行"}
              </strong>
            </div>
            <div>
              <span>モジュールキー</span>
              <strong>{previewItem.module_key ?? "自動採番"}</strong>
            </div>
            <div>
              <span>装置数</span>
              <strong>{previewItem.device_headers.length}</strong>
            </div>
            <p>{importPreviewState.message}</p>
          </section>
          <div className="preview-surface preview-surface-sheet">
            <ExcelModulePreview item={previewModuleItem} mode="fullscreen" />
          </div>
          <details className="json-preview-wrap">
            <summary>正規化結果を表示</summary>
            <pre className="json-preview">{JSON.stringify(previewItem, null, 2)}</pre>
          </details>
        </PreviewOverlay>
      ) : null}

    </Page>
  );
}

function DocumentSearchPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialKeyword = searchParams.get("keyword") ?? "";
  const initialStatus = (searchParams.get("status") ?? "all") as (typeof moduleStatusOptions)[number]["value"];
  const initialCreatedBy = searchParams.get("created_by") ?? "";
  const initialUpdatedFrom = searchParams.get("updated_from") ?? "";
  const initialUpdatedTo = searchParams.get("updated_to") ?? "";
  const initialModuleName = searchParams.get("module_name") ?? "";
  const initialSort = searchParams.get("sort") ?? "key_asc";
  const [keywordInput, setKeywordInput] = useState(initialKeyword);
  const [statusInput, setStatusInput] = useState(initialStatus);
  const [createdByInput, setCreatedByInput] = useState(initialCreatedBy);
  const [updatedFromInput, setUpdatedFromInput] = useState(initialUpdatedFrom);
  const [updatedToInput, setUpdatedToInput] = useState(initialUpdatedTo);
  const [moduleNameInput, setModuleNameInput] = useState(initialModuleName);
  const [sortInput, setSortInput] = useState(initialSort);
  const keyword = initialKeyword;
  const statusFilter = initialStatus;
  const createdByFilter = initialCreatedBy;
  const updatedFromFilter = initialUpdatedFrom;
  const updatedToFilter = initialUpdatedTo;
  const moduleNameFilter = initialModuleName;
  const sortFilter = initialSort;
  const [sourceDocListState, setSourceDocListState] = useState<SourceDocListState>({
    status: "loading",
    items: [],
    message: "原本一覧を取得しています。",
  });

  useEffect(() => {
    setKeywordInput(initialKeyword);
    setStatusInput(initialStatus);
    setCreatedByInput(initialCreatedBy);
    setUpdatedFromInput(initialUpdatedFrom);
    setUpdatedToInput(initialUpdatedTo);
    setModuleNameInput(initialModuleName);
    setSortInput(initialSort);
  }, [initialKeyword, initialStatus, initialCreatedBy, initialUpdatedFrom, initialUpdatedTo, initialModuleName, initialSort]);

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchSourceDocs(): Promise<void> {
      setSourceDocListState({ status: "loading", items: [], message: "原本一覧を取得しています。" });

      try {
        const endpoint = new URL(buildApiUrl("/api/v1/source-docs"), window.location.origin);

        if (keyword) endpoint.searchParams.set("keyword", keyword);
        if (statusFilter !== "all") endpoint.searchParams.set("status", statusFilter);
        if (createdByFilter) endpoint.searchParams.set("created_by", createdByFilter);
        if (updatedFromFilter) endpoint.searchParams.set("updated_from", updatedFromFilter);
        if (updatedToFilter) endpoint.searchParams.set("updated_to", updatedToFilter);
        if (moduleNameFilter) endpoint.searchParams.set("module_name", moduleNameFilter);
        if (sortFilter !== "key_asc") endpoint.searchParams.set("sort", sortFilter);

        const response = await fetch(endpoint.toString(), { signal: abortController.signal });
        const responseBody = (await response.json()) as ApiResponse<SourceDocListData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setSourceDocListState({ status: "unavailable", items: [], message: responseBody.message || "原本一覧の取得に失敗しました。HTTP " + response.status });
          return;
        }

        setSourceDocListState({ status: "available", items: responseBody.data.items, message: responseBody.message || "原本一覧を取得しました。" });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setSourceDocListState({ status: "unavailable", items: [], message: "APIに接続できませんでした。" });
      }
    }

    void fetchSourceDocs();

    return () => abortController.abort();
  }, [keyword, statusFilter, createdByFilter, updatedFromFilter, updatedToFilter, moduleNameFilter, sortFilter]);

  function navigateWithFilters(filters: {
    keyword: string;
    status: (typeof moduleStatusOptions)[number]["value"];
    createdBy: string;
    updatedFrom: string;
    updatedTo: string;
    moduleName: string;
    sort: string;
  }): void {
    const params = new URLSearchParams();
    const normalizedKeyword = filters.keyword.trim();
    const normalizedCreatedBy = filters.createdBy.trim();
    const normalizedModuleName = filters.moduleName.trim();

    if (normalizedKeyword) params.set("keyword", normalizedKeyword);
    if (filters.status !== "all") params.set("status", filters.status);
    if (normalizedCreatedBy) params.set("created_by", normalizedCreatedBy);
    if (filters.updatedFrom) params.set("updated_from", filters.updatedFrom);
    if (filters.updatedTo) params.set("updated_to", filters.updatedTo);
    if (normalizedModuleName) params.set("module_name", normalizedModuleName);
    if (filters.sort !== "key_asc") params.set("sort", filters.sort);

    const nextQuery = params.toString();
    navigate(nextQuery ? "/documents/search?" + nextQuery : "/documents/search");
  }

  function handleSubmit(): void {
    navigateWithFilters({ keyword: keywordInput, status: statusInput, createdBy: createdByInput, updatedFrom: updatedFromInput, updatedTo: updatedToInput, moduleName: moduleNameInput, sort: sortInput });
  }

  function handleStatusFilterChange(nextStatus: (typeof moduleStatusOptions)[number]["value"]): void {
    setStatusInput(nextStatus);
    navigateWithFilters({ keyword, status: nextStatus, createdBy: createdByFilter, updatedFrom: updatedFromFilter, updatedTo: updatedToFilter, moduleName: moduleNameFilter, sort: sortFilter });
  }

  const statusFilterLabel = moduleStatusOptions.find((option) => option.value === statusFilter)?.label ?? statusFilter;

  return (
    <Page title={"原本検索"} description={"APIから取得した原本一覧を検索し、関連モジュールと詳細情報を確認できます。"}>
      <form className="search-form module-search-form" onSubmit={(event) => { event.preventDefault(); handleSubmit(); }}>
        <label>{"キーワード"}<input placeholder="例: M1確認用 / MOD-001 / 原本A" value={keywordInput} onChange={(event) => setKeywordInput(event.target.value)} /></label>
        <label>{"承認状態"}<select value={statusInput} onChange={(event) => setStatusInput(event.target.value as (typeof moduleStatusOptions)[number]["value"])}>{moduleStatusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <label>{"作成者"}<input placeholder="seed / webui" value={createdByInput} onChange={(event) => setCreatedByInput(event.target.value)} /></label>
        <label>
          {"更新日"}
          <input
            type="date"
            value={updatedFromInput}
            onChange={(event) => {
              setUpdatedFromInput(event.target.value);
              setUpdatedToInput(event.target.value);
            }}
          />
        </label>
        <label>{"利用モジュール"}<input placeholder="MOD-001 / ボーレート" value={moduleNameInput} onChange={(event) => setModuleNameInput(event.target.value)} /></label>
        <label>{"並び替え"}<select value={sortInput} onChange={(event) => setSortInput(event.target.value)}><option value="key_asc">{"ID昇順"}</option><option value="key_desc">{"ID降順"}</option><option value="updated_desc">{"更新日が新しい順"}</option><option value="updated_asc">{"更新日が古い順"}</option><option value="status_asc">{"承認状態順"}</option></select></label>
        <button className="primary" type="submit"><span aria-hidden="true">⌕</span>{"検索"}</button>
      </form>

      <section className={"list-status list-status-" + sourceDocListState.status} aria-live="polite">
        <div><span>{"取得状態"}</span><strong>{sourceDocListState.status === "loading" ? "取得中" : sourceDocListState.status === "available" ? "取得完了" : "取得失敗"}</strong></div>
        <div><span>{"検索キーワード"}</span><strong>{keyword || "指定なし"}</strong></div>
        <div><span>{"承認状態"}</span><strong>{statusFilterLabel}</strong></div>
        <div><span>{"利用モジュール"}</span><strong>{moduleNameFilter || "指定なし"}</strong></div>
        <p>{sourceDocListState.message}</p>
      </section>

      <section className="approval-flow" aria-label="原本承認状態フィルター">
        {moduleStatusOptions.map((option) => <button key={option.value} type="button" className={option.value === statusFilter ? "approval-filter-button active" : "approval-filter-button"} onClick={() => handleStatusFilterChange(option.value)}>{option.label}</button>)}
      </section>

      <Toolbar>
        <button className="secondary" onClick={() => navigate("/documents/search")}><span aria-hidden="true">↺</span>{"条件をリセット"}</button>
        <button className="primary" onClick={() => navigate("/documents/create")}><span aria-hidden="true">+</span>{"原本登録"}</button>
      </Toolbar>
      {sourceDocListState.status === "available" && sourceDocListState.items.length === 0 ? (
        <section className="empty-state"><h2>{"該当する原本はありません"}</h2><p>{"検索条件を変えて再度確認してください。"}</p></section>
      ) : (
        <DataTable
          columns={["原本ID", "原本名", "版", "状態", "利用モジュール", "有効数", "作成者", "更新日", "操作"]}
          rows={sourceDocListState.items.map((item) => [item.source_doc_key, item.source_doc_name, formatVersionLabel(item), <ModuleStatusPill status={item.status} label={item.status_label} />, item.module_names.join(", ") || "-", item.enabled_module_count + "/" + item.module_count, item.created_by ?? "-", item.updated_at, <button className="text-button" onClick={() => navigate("/documents/" + item.source_doc_id)}>{"詳細"}</button>])}
        />
      )}
    </Page>
  );
}

function LegacyDocumentEditPage() {
  const navigate = useNavigate();
  const [sourceDocKeyInput, setSourceDocKeyInput] = useState("");
  const [sourceDocNameInput, setSourceDocNameInput] = useState("M1 procedure bundle");
  const [descriptionInput, setDescriptionInput] = useState("原本登録画面から作成。");
  const [changeNoteInput, setChangeNoteInput] = useState("初版作成");
  const [createdByInput, setCreatedByInput] = useState("webui");
  const [moduleListState, setModuleListState] = useState<ModuleListState>({
    status: "loading",
    items: [],
    message: "利用可能なモジュールを取得しています。",
  });
  const [itemSeed, setItemSeed] = useState(2);
  const [items, setItems] = useState<SourceDocCreateItemDraft[]>([
    { rowId: 1, moduleId: "", enabled: true },
  ]);
  const [createState, setCreateState] = useState<SourceDocCreateState>({
    status: "idle",
    item: null,
    message: "モジュールを選択して原本の初版を保存します。",
  });

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchModules(): Promise<void> {
      setModuleListState({
        status: "loading",
        items: [],
        message: "利用可能なモジュールを取得しています。",
      });

      try {
        const endpoint = new URL(buildApiUrl("/api/v1/modules"), window.location.origin);
        endpoint.searchParams.set("status", "published");
        const response = await fetch(endpoint.toString(), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<ModuleListData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setModuleListState({
            status: "unavailable",
            items: [],
            message: responseBody.message || `モジュール一覧の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        setModuleListState({
          status: "available",
          items: responseBody.data.items,
          message: responseBody.message || "承認済みモジュールを取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setModuleListState({
          status: "unavailable",
          items: [],
          message: "モジュール一覧を API から取得できませんでした。",
        });
      }
    }

    void fetchModules();

    return () => {
      abortController.abort();
    };
  }, []);

  function updateItemModule(rowId: number, moduleId: string): void {
    setItems((currentItems) =>
      currentItems.map((item) => (item.rowId === rowId ? { ...item, moduleId } : item)),
    );
  }

  function updateItemEnabled(rowId: number, enabled: boolean): void {
    setItems((currentItems) =>
      currentItems.map((item) => (item.rowId === rowId ? { ...item, enabled } : item)),
    );
  }

  function addItem(): void {
    setItems((currentItems) => [...currentItems, { rowId: itemSeed, moduleId: "", enabled: true }]);
    setItemSeed((currentSeed) => currentSeed + 1);
  }

  function removeItem(rowId: number): void {
    setItems((currentItems) => (currentItems.length > 1 ? currentItems.filter((item) => item.rowId !== rowId) : currentItems));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    const selectedItems = items
      .map((item, index) => ({
        module_id: Number(item.moduleId),
        enabled: item.enabled,
        item_order: index + 1,
      }))
      .filter((item) => Number.isInteger(item.module_id) && item.module_id > 0);

    if (!sourceDocNameInput.trim()) {
      setCreateState({
        status: "error",
        item: null,
        message: "原本名は必須です。",
      });
      return;
    }

    if (selectedItems.length === 0) {
      setCreateState({
        status: "error",
        item: null,
        message: "モジュールを1件以上選択してください。",
      });
      return;
    }

    setCreateState({
      status: "submitting",
      item: null,
      message: "原本と初版を保存しています。",
    });

    try {
      const response = await fetch(buildApiUrl("/api/v1/source-docs"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          source_doc_key: sourceDocKeyInput.trim() || undefined,
          source_doc_name: sourceDocNameInput.trim(),
          description: descriptionInput.trim() || undefined,
          change_note: changeNoteInput.trim() || undefined,
          created_by: createdByInput.trim() || undefined,
          items: selectedItems,
        }),
      });

      const responseBody = (await response.json()) as ApiResponse<SourceDocDetailData>;

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setCreateState({
          status: "error",
          item: null,
          message: responseBody.message || `原本作成に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setCreateState({
        status: "success",
        item: responseBody.data,
        message: responseBody.message || "原本を作成しました。",
      });
      setSourceDocKeyInput(responseBody.data.source_doc_key);
    } catch (error) {
      setCreateState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : "原本作成に失敗しました。",
      });
    }
  }

  const createdItem = createState.item;

  return (
    <Page title="原本作成 / 更新" description="モジュールを組み合わせて原本の初版を保存します。POST /api/v1/source-docs の結果をこの画面から確認できます。">
      <form className="register-form" onSubmit={handleSubmit}>
        <FormGrid>
          <label>
            原本キー
            <input
              value={sourceDocKeyInput}
              onChange={(event) => setSourceDocKeyInput(event.target.value)}
              placeholder="BP-STD-003 未入力時は自動採番"
            />
          </label>
          <label>
            原本名
            <input value={sourceDocNameInput} onChange={(event) => setSourceDocNameInput(event.target.value)} required />
          </label>
          <label>
            作成者
            <input value={createdByInput} onChange={(event) => setCreatedByInput(event.target.value)} />
          </label>
          <label>
            変更メモ
            <input value={changeNoteInput} onChange={(event) => setChangeNoteInput(event.target.value)} />
          </label>
          <label className="wide">
            説明
            <textarea value={descriptionInput} onChange={(event) => setDescriptionInput(event.target.value)} />
          </label>
        </FormGrid>

        <section className="register-step-card">
          <div className="register-step-header">
            <h2>利用モジュール</h2>
            <button className="secondary" type="button" onClick={addItem}>
              <span aria-hidden="true">＋</span>行追加
            </button>
          </div>
          <section className={`list-status list-status-${moduleListState.status}`} aria-live="polite">
            <div>
              <span>取得状態</span>
              <strong>
                {moduleListState.status === "loading"
                  ? "取得中"
                  : moduleListState.status === "available"
                    ? "取得成功"
                    : "取得失敗"}
              </strong>
            </div>
            <div>
              <span>利用可能数</span>
              <strong>{moduleListState.items.length}</strong>
            </div>
            <div>
              <span>先頭キー</span>
              <strong>{moduleListState.items[0]?.module_key ?? "-"}</strong>
            </div>
            <p>{moduleListState.message}</p>
          </section>
          <div className="register-rows">
            {items.map((item, index) => (
              <section key={item.rowId} className="register-row-editor">
                <div className="register-row-editor-header">
                  <strong>行 {index + 1}</strong>
                  <button className="text-button" type="button" onClick={() => removeItem(item.rowId)} disabled={items.length === 1}>
                    <span aria-hidden="true">−</span>削除
                  </button>
                </div>
                <div className="register-step-grid">
                  <label>
                    モジュール
                    <select
                      value={item.moduleId}
                      onChange={(event) => updateItemModule(item.rowId, event.target.value)}
                      required
                    >
                      <option value="">選択してください</option>
                      {moduleListState.items.map((module) => (
                        <option key={module.module_id} value={String(module.module_id)}>
                          {`${module.module_key} ${module.module_name}`}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="checkbox-field">
                    有効
                    <input
                      type="checkbox"
                      checked={item.enabled}
                      onChange={(event) => updateItemEnabled(item.rowId, event.target.checked)}
                    />
                  </label>
                </div>
              </section>
            ))}
          </div>
        </section>

        <section
          className={`register-status ${
            createState.status === "success"
              ? "register-status-success"
              : createState.status === "error"
                ? "register-status-error"
                : createState.status === "submitting"
                  ? "register-status-submitting"
                  : ""
          }`}
        >
          <span>保存状態</span>
          <strong>
            {createState.status === "success"
              ? "保存完了"
              : createState.status === "error"
                ? "保存失敗"
                : createState.status === "submitting"
                  ? "保存中"
                  : "入力待ち"}
          </strong>
          <p>{createState.message}</p>
          {createdItem ? (
            <div className="register-result-meta">
              <span>{createdItem.source_doc_key}</span>
              <span>{`版 ${formatVersionLabel(createdItem)}`}</span>
              <span>{createdItem.status_label}</span>
            </div>
          ) : null}
        </section>

        <Toolbar>
          <button className="secondary" type="button" onClick={() => navigate("/documents/search")}>
            <span aria-hidden="true">↩</span>一覧へ戻る
          </button>
          {createdItem ? (
            <button className="secondary" type="button" onClick={() => navigate(`/documents/${createdItem.source_doc_id}`)}>
              <span aria-hidden="true">↗</span>詳細を開く
            </button>
          ) : null}
          <button className="primary" type="submit" disabled={createState.status === "submitting"}>
            <span aria-hidden="true">✎</span>{createState.status === "submitting" ? "保存中..." : "保存実行"}
          </button>
        </Toolbar>
      </form>
    </Page>
  );
}

function DocumentEditPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editSourceDocIdParam = searchParams.get("id");
  const editSourceDocId =
    editSourceDocIdParam && /^\d+$/.test(editSourceDocIdParam) ? Number(editSourceDocIdParam) : null;
  const initialModuleIdParam = searchParams.get("module_id");
  const initialModuleId =
    initialModuleIdParam && /^\d+$/.test(initialModuleIdParam) ? initialModuleIdParam : "";
  const isEditMode = editSourceDocId !== null;
  const [sourceDocKeyInput, setSourceDocKeyInput] = useState("");
  const [sourceDocNameInput, setSourceDocNameInput] = useState("M1 procedure bundle");
  const [descriptionInput, setDescriptionInput] = useState("原本登録画面から作成。");
  const [changeNoteInput, setChangeNoteInput] = useState("初版作成");
  const [createdByInput, setCreatedByInput] = useState("webui");
  const [formLoadState, setFormLoadState] = useState<SourceDocFormLoadState>({
    status: "idle",
    message: "新規作成モードです。入力後に保存を実行してください。",
  });
  const [moduleListState, setModuleListState] = useState<ModuleListState>({
    status: "loading",
    items: [],
    message: "利用可能なモジュールを取得しています。",
  });
  const [itemSeed, setItemSeed] = useState(2);
  const [items, setItems] = useState<SourceDocCreateItemDraft[]>([{ rowId: 1, moduleId: initialModuleId, enabled: true }]);
  const [createState, setCreateState] = useState<SourceDocCreateState>({
    status: "idle",
    item: null,
    message: "モジュールを選択して原本を保存してください。",
  });

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchModules(): Promise<void> {
      setModuleListState({
        status: "loading",
        items: [],
        message: "利用可能なモジュールを取得しています。",
      });

      try {
        const endpoint = new URL(buildApiUrl("/api/v1/modules"), window.location.origin);
        endpoint.searchParams.set("status", "published");
        const response = await fetch(endpoint.toString(), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<ModuleListData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setModuleListState({
            status: "unavailable",
            items: [],
            message: responseBody.message || `モジュール一覧の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        setModuleListState({
          status: "available",
          items: responseBody.data.items,
          message: responseBody.message || "承認済みモジュールを取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setModuleListState({
          status: "unavailable",
          items: [],
          message: "モジュール一覧を API から取得できませんでした。",
        });
      }
    }

    void fetchModules();

    return () => {
      abortController.abort();
    };
  }, []);

  useEffect(() => {
    if (!isEditMode || editSourceDocId === null) {
      setFormLoadState({
        status: "idle",
        message: "新規作成モードです。入力後に保存を実行してください。",
      });
      return;
    }

    const abortController = new AbortController();

    async function fetchSourceDocForEdit(): Promise<void> {
      setFormLoadState({
        status: "loading",
        message: "更新対象の原本を読み込んでいます。",
      });

      try {
        const response = await fetch(buildApiUrl(`/api/v1/source-docs/${editSourceDocId}`), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<SourceDocDetailData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setFormLoadState({
            status: "error",
            message: responseBody.message || `更新対象の原本取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        const detail = responseBody.data;
        setSourceDocKeyInput(detail.source_doc_key);
        setSourceDocNameInput(detail.source_doc_name);
        setDescriptionInput(detail.description ?? "");
        setChangeNoteInput(detail.change_note ?? "更新版作成");
        setCreatedByInput(detail.created_by ?? "webui");
        setItems(
          detail.items.length > 0
            ? detail.items.map((item, index) => ({
                rowId: index + 1,
                moduleId: String(item.module_id),
                enabled: item.enabled,
              }))
            : [{ rowId: 1, moduleId: "", enabled: true }],
        );
        setItemSeed((detail.items.length || 1) + 1);
        setCreateState({
          status: "idle",
          item: null,
          message: "原本の更新内容を編集して保存してください。",
        });
        setFormLoadState({
          status: "ready",
          message: `${detail.source_doc_key} を更新モードで読み込みました。`,
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setFormLoadState({
          status: "error",
          message: error instanceof Error ? error.message : "更新対象の原本取得に失敗しました。",
        });
      }
    }

    void fetchSourceDocForEdit();

    return () => {
      abortController.abort();
    };
  }, [editSourceDocId, isEditMode]);

  function updateItemModule(rowId: number, moduleId: string): void {
    setItems((currentItems) =>
      currentItems.map((item) => (item.rowId === rowId ? { ...item, moduleId } : item)),
    );
  }

  function updateItemEnabled(rowId: number, enabled: boolean): void {
    setItems((currentItems) =>
      currentItems.map((item) => (item.rowId === rowId ? { ...item, enabled } : item)),
    );
  }

  function addItem(): void {
    setItems((currentItems) => [...currentItems, { rowId: itemSeed, moduleId: "", enabled: true }]);
    setItemSeed((currentSeed) => currentSeed + 1);
  }

  function removeItem(rowId: number): void {
    setItems((currentItems) => (currentItems.length > 1 ? currentItems.filter((item) => item.rowId !== rowId) : currentItems));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    const selectedItems = items
      .map((item, index) => ({
        module_id: Number(item.moduleId),
        enabled: item.enabled,
        item_order: index + 1,
      }))
      .filter((item) => Number.isInteger(item.module_id) && item.module_id > 0);

    if (!sourceDocNameInput.trim()) {
      setCreateState({
        status: "error",
        item: null,
        message: "原本名は必須です。",
      });
      return;
    }

    if (selectedItems.length === 0) {
      setCreateState({
        status: "error",
        item: null,
        message: "モジュールを1件以上選択してください。",
      });
      return;
    }

    setCreateState({
      status: "submitting",
      item: null,
      message: isEditMode ? "原本の更新内容を保存しています。" : "原本と関連モジュールを保存しています。",
    });

    try {
      const response = await fetch(
        buildApiUrl(isEditMode && editSourceDocId !== null ? `/api/v1/source-docs/${editSourceDocId}` : "/api/v1/source-docs"),
        {
          method: isEditMode ? "PUT" : "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            source_doc_key: sourceDocKeyInput.trim() || undefined,
            source_doc_name: sourceDocNameInput.trim(),
            description: descriptionInput.trim() || undefined,
            change_note: changeNoteInput.trim() || undefined,
            created_by: createdByInput.trim() || undefined,
            items: selectedItems,
          }),
        },
      );

      const responseBody = (await response.json()) as ApiResponse<SourceDocDetailData>;

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setCreateState({
          status: "error",
          item: null,
          message: responseBody.message || `${isEditMode ? "原本更新" : "原本作成"}に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setCreateState({
        status: "success",
        item: responseBody.data,
        message: responseBody.message || (isEditMode ? "原本を更新しました。" : "原本を保存しました。"),
      });
      setSourceDocKeyInput(responseBody.data.source_doc_key);
      if (isEditMode) {
        setFormLoadState({
          status: "ready",
          message: `${responseBody.data.source_doc_key} を更新しました。現在は版 ${formatVersionLabel(responseBody.data)} です。`,
        });
      }
    } catch (error) {
      setCreateState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : `${isEditMode ? "原本更新" : "原本作成"}に失敗しました。`,
      });
    }
  }

  const createdItem = createState.item;
  const submitDisabled = createState.status === "submitting" || (isEditMode && formLoadState.status === "loading");

  return (
    <Page
      title="原本作成 / 更新"
      description={
        isEditMode
          ? "既存の原本を読み込み、更新版を保存します。PUT /api/v1/source-docs/{source_doc_id} をこの画面から確認できます。"
          : "モジュールを組み合わせて原本の初版を保存します。POST /api/v1/source-docs の結果をこの画面から確認できます。"
      }
    >
      <form className="register-form" onSubmit={handleSubmit}>
        <section
          className={`register-status ${
            formLoadState.status === "ready"
              ? "register-status-success"
              : formLoadState.status === "error"
                ? "register-status-error"
                : formLoadState.status === "loading"
                  ? "register-status-submitting"
                  : ""
          }`}
        >
          <span>編集モード</span>
          <strong>{isEditMode ? "更新" : "新規作成"}</strong>
          <p>{formLoadState.message}</p>
          {editSourceDocId !== null ? (
            <div className="register-result-meta">
              <span>source_doc_id {editSourceDocId}</span>
              <span>{sourceDocKeyInput || "-"}</span>
            </div>
          ) : null}
        </section>

        <FormGrid>
          <label>
            原本キー
            <input
              value={sourceDocKeyInput}
              onChange={(event) => setSourceDocKeyInput(event.target.value)}
              placeholder="BP-STD-003 未入力時は自動採番"
            />
          </label>
          <label>
            原本名
            <input value={sourceDocNameInput} onChange={(event) => setSourceDocNameInput(event.target.value)} required />
          </label>
          <label>
            作成者
            <input value={createdByInput} onChange={(event) => setCreatedByInput(event.target.value)} />
          </label>
          <label>
            変更メモ
            <input value={changeNoteInput} onChange={(event) => setChangeNoteInput(event.target.value)} />
          </label>
          <label className="wide">
            説明
            <textarea value={descriptionInput} onChange={(event) => setDescriptionInput(event.target.value)} />
          </label>
        </FormGrid>

        <section className="register-step-card">
          <div className="register-step-header">
            <h2>利用モジュール</h2>
            <button className="secondary" type="button" onClick={addItem}>
              <span aria-hidden="true">＋</span>行追加
            </button>
          </div>
          <section className={`list-status list-status-${moduleListState.status}`} aria-live="polite">
            <div>
              <span>取得状態</span>
              <strong>
                {moduleListState.status === "loading"
                  ? "取得中"
                  : moduleListState.status === "available"
                    ? "取得成功"
                    : "取得失敗"}
              </strong>
            </div>
            <div>
              <span>利用可能数</span>
              <strong>{moduleListState.items.length}</strong>
            </div>
            <div>
              <span>先頭キー</span>
              <strong>{moduleListState.items[0]?.module_key ?? "-"}</strong>
            </div>
            <p>{moduleListState.message}</p>
          </section>
          <div className="register-rows">
            {items.map((item, index) => (
              <section key={item.rowId} className="register-row-editor">
                <div className="register-row-editor-header">
                  <strong>行 {index + 1}</strong>
                  <button className="text-button" type="button" onClick={() => removeItem(item.rowId)} disabled={items.length === 1}>
                    <span aria-hidden="true">−</span>削除
                  </button>
                </div>
                <div className="register-step-grid">
                  <label>
                    モジュール
                    <select
                      value={item.moduleId}
                      onChange={(event) => updateItemModule(item.rowId, event.target.value)}
                      required
                    >
                      <option value="">選択してください</option>
                      {moduleListState.items.map((module) => (
                        <option key={module.module_id} value={String(module.module_id)}>
                          {`${module.module_key} ${module.module_name}`}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="checkbox-field">
                    有効
                    <input
                      type="checkbox"
                      checked={item.enabled}
                      onChange={(event) => updateItemEnabled(item.rowId, event.target.checked)}
                    />
                  </label>
                </div>
              </section>
            ))}
          </div>
        </section>

        <section
          className={`register-status ${
            createState.status === "success"
              ? "register-status-success"
              : createState.status === "error"
                ? "register-status-error"
                : createState.status === "submitting"
                  ? "register-status-submitting"
                  : ""
          }`}
        >
          <span>保存状態</span>
          <strong>
            {createState.status === "success"
              ? isEditMode
                ? "更新完了"
                : "保存完了"
              : createState.status === "error"
                ? "保存失敗"
                : createState.status === "submitting"
                  ? "保存中"
                  : "入力待ち"}
          </strong>
          <p>{createState.message}</p>
          {createdItem ? (
            <div className="register-result-meta">
              <span>{createdItem.source_doc_key}</span>
              <span>{`版 ${formatVersionLabel(createdItem)}`}</span>
              <span>{createdItem.status_label}</span>
            </div>
          ) : null}
        </section>

        <Toolbar>
          <button className="secondary" type="button" onClick={() => navigate("/documents/search")}>
            <span aria-hidden="true">←</span>一覧へ戻る
          </button>
          {createdItem ? (
            <button className="secondary" type="button" onClick={() => navigate(`/documents/${createdItem.source_doc_id}`)}>
              <span aria-hidden="true">↗</span>詳細を開く
            </button>
          ) : null}
          <button className="primary" type="submit" disabled={submitDisabled}>
            <span aria-hidden="true">✎</span>
            {createState.status === "submitting" ? "保存中..." : isEditMode ? "更新実行" : "保存実行"}
          </button>
        </Toolbar>
      </form>
    </Page>
  );
}

function useSourceDocDetailState(id: string | undefined): SourceDocDetailState {
  const [sourceDocDetailState, setSourceDocDetailState] = useState<SourceDocDetailState>({
    status: "loading",
    item: null,
    message: "原本詳細を取得しています...",
  });

  useEffect(() => {
    if (!id) {
      setSourceDocDetailState({
        status: "unavailable",
        item: null,
        message: "原本IDが指定されていません。",
      });
      return;
    }

    const abortController = new AbortController();

    setSourceDocDetailState({
      status: "loading",
      item: null,
      message: "原本詳細を取得しています...",
    });

    async function fetchSourceDocDetail(): Promise<void> {
      try {
        const response = await fetch(buildApiUrl(`/api/v1/source-docs/${id}`), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<SourceDocDetailData>;

        if (!response.ok || responseBody.result !== "success" || !responseBody.data) {
          setSourceDocDetailState({
            status: "unavailable",
            item: null,
            message: responseBody.message || `原本詳細の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        setSourceDocDetailState({
          status: "available",
          item: responseBody.data,
          message: responseBody.message || "原本詳細を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setSourceDocDetailState({
          status: "unavailable",
          item: null,
          message: "APIに接続できませんでした。",
        });
      }
    }

    void fetchSourceDocDetail();

    return () => {
      abortController.abort();
    };
  }, [id]);

  return sourceDocDetailState;
}

function DocumentDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const sourceDocDetailState = useSourceDocDetailState(id);
  const item = sourceDocDetailState.item;
  const [isPreviewOverlayOpen, setIsPreviewOverlayOpen] = useState(false);
  const isSourceDocLocked = item?.status === "review_requested";
  const canCreateCaseDoc = item?.status === "published";

  return (
    <Page title="原本詳細" description="原本の版、状態、関連モジュール構成を API から確認します。">
      <section className={`list-status list-status-${sourceDocDetailState.status}`} aria-live="polite">
        <div>
          <span>取得状態</span>
          <strong>
            {sourceDocDetailState.status === "loading"
              ? "取得中"
              : sourceDocDetailState.status === "available"
                ? "取得成功"
                : "取得失敗"}
          </strong>
        </div>
        <div>
          <span>原本ID</span>
          <strong>{id ?? "未指定"}</strong>
        </div>
        <div>
          <span>関連モジュール数</span>
          <strong>{item ? item.module_count : "-"}</strong>
        </div>
        <p>{sourceDocDetailState.message}</p>
      </section>
      <Toolbar>
        <button className="secondary" onClick={() => navigate("/documents/search")}>
          <span aria-hidden="true">↩</span>
          一覧へ戻る
        </button>
        <button className="secondary" onClick={() => setIsPreviewOverlayOpen(true)} disabled={!item}>
          <span aria-hidden="true">□</span>
          全画面プレビュー
        </button>
        <button
          className={canCreateCaseDoc ? "secondary" : "primary"}
          disabled={!item || isSourceDocLocked}
          title={isSourceDocLocked ? "承認依頼中のため更新できません。" : "原本を更新します。"}
          onClick={() => {
            if (item) {
              navigate(`/documents/create?id=${item.source_doc_id}`);
            }
          }}
        >
          <span aria-hidden="true">✎</span>
          更新する
        </button>
        <button
          className="primary"
          disabled={!canCreateCaseDoc}
          title={canCreateCaseDoc ? "この原本を選択した状態で案件化へ進みます。" : "承認済みの原本だけを案件化できます。"}
          onClick={() => item && navigate(`/case-docs?source_doc_id=${item.source_doc_id}`)}
        >
          <span aria-hidden="true">CS</span>
          この原本から案件化
        </button>
      </Toolbar>
      {item ? (
        <>
          {isSourceDocLocked ? (
            <div className="approval-lock-note">
              <strong>承認依頼中です</strong>
              <span>承認者の確認待ちのため、この原本は更新できません。</span>
            </div>
          ) : null}
          <section className="detail-layout">
            <div className="facts">
              <Fact label="原本ID" value={item.source_doc_key} />
              <Fact label="原本名" value={item.source_doc_name} />
              <Fact label="版" value={formatVersionLabel(item)} />
              <Fact label="状態" value={item.status_label} />
              <Fact label="作成者" value={item.created_by ?? "-"} />
              <Fact label="更新日" value={item.updated_at} />
            </div>
            <div className="module-detail-note">
              <span>説明</span>
              <p>{item.description ?? "説明は未設定です。"}</p>
              <span>変更メモ</span>
              <p>{item.change_note ?? "変更メモは未設定です。"}</p>
            </div>
          </section>
        </>
      ) : (
        <section className="empty-state">
          <h2>原本詳細を表示できません</h2>
          <p>{sourceDocDetailState.message}</p>
        </section>
      )}

      {item && isPreviewOverlayOpen ? (
        <PreviewOverlay
          title={`${item.source_doc_name} / 原本プレビュー`}
          description="原本に紐づくモジュール構成を、同ページ内の全画面 overlay で確認します。"
          onClose={() => setIsPreviewOverlayOpen(false)}
          actions={
            <button className="secondary" type="button" onClick={() => window.print()}>
              <span aria-hidden="true">P</span>
              印刷
            </button>
          }
        >
          <div className="preview-surface">
            <ExcelSourceDocPreview item={item} onOpenModule={(moduleId) => navigate(`/modules/${moduleId}`)} />
          </div>
        </PreviewOverlay>
      ) : null}
    </Page>
  );
}

function ExcelSourceDocPreview({
  item,
  onOpenModule,
}: {
  item: SourceDocDetailData;
  onOpenModule: (moduleId: number) => void;
}) {
  const moduleNames = item.items.map((module) => module.module_name);

  return (
    <section className="excel-preview" aria-label="Excel風原本プレビュー">
      <div className="excel-title-grid">
        <div className="excel-cell excel-title-cell">{item.source_doc_name}</div>
        <div className="excel-cell excel-small-heading">版</div>
        <div className="excel-cell excel-small-heading">状態</div>
        <div className="excel-cell excel-small-heading">有効</div>
        <div className="excel-cell excel-device-cell">関連モジュール</div>
        <div className="excel-cell excel-sequence-cell">{formatVersionLabel(item)}</div>
        <div className="excel-cell excel-target-value">{item.status_label}</div>
        <div className="excel-cell excel-target-value">{`${item.enabled_module_count}/${item.module_count}`}</div>
        <div className="excel-cell excel-device-value">{moduleNames.join(", ") || "-"}</div>
      </div>

      {item.items.map((module) => {
        const deviceHeaders = getSourceDocModuleDeviceHeaders(module);

        return (
          <article key={module.blueprint_item_id} className="source-doc-module-block">
          <header className="source-doc-module-header">
            <div>
              <span>順序 {module.item_order}</span>
              <strong>{module.module_name}</strong>
            </div>
            <div className="source-doc-module-meta">
              <ModuleStatusPill status={module.module_status} label={module.module_status_label} />
              <span>{module.enabled ? "有効" : "無効"}</span>
              <span>{`v${module.module_version_no}`}</span>
              <button className="text-button" onClick={() => onOpenModule(module.module_id)}>
                モジュール詳細
              </button>
            </div>
          </header>

          <div className="excel-sheet-wrap excel-sheet-scroll-with-sticky-left excel-sheet-scroll-source">
            <table className="excel-sheet excel-sheet-sticky-left excel-sheet-source-sticky">
              <colgroup>
                <col className="excel-col-small" />
                <col className="excel-col-small" />
                <col className="excel-col-small" />
                <col className="excel-col-doc" />
                <col className="excel-col-work" />
                <col className="excel-col-check" />
                {deviceHeaders.map((header) => (
                  <Fragment key={"source-cols-" + module.blueprint_item_id + "-" + header.slot_no}>
                    <col className="excel-col-time" />
                    <col className="excel-col-window" />
                    <col className="excel-col-prompt" />
                    <col className="excel-col-command" />
                  </Fragment>
                ))}
              </colgroup>
              <thead>
                <tr>
                  <th>大</th>
                  <th>中</th>
                  <th>小</th>
                  <th>技術資料名</th>
                  <th>作業内容</th>
                  <th>確認事項 or 項目</th>
                  {deviceHeaders.map((header) => (
                    <Fragment key={"source-header-" + module.blueprint_item_id + "-" + header.slot_no}>
                      <th>時刻</th>
                      <th>window</th>
                      <th>P</th>
                      <th>コマンド</th>
                    </Fragment>
                  ))}
                </tr>
              </thead>
              <tbody>
                {buildIndentedRows(module.rows).map(({ row, indentLevel }) => (
                  <tr key={`${module.blueprint_item_id}-${row.module_row_id}`} className={`excel-row excel-row-${row.row_type}`}>
                    <td className="excel-number">{row.major_no ?? ""}</td>
                    <td className="excel-number">{row.middle_no ?? ""}</td>
                    <td className="excel-number">{row.minor_no ?? ""}</td>
                    <td>{row.tech_doc_text ?? ""}</td>
                    <td className="excel-work-cell">
                      <IndentedExcelText text={row.work_text} indentLevel={indentLevel} />
                      <ModuleRowImageList images={row.images ?? []} placement="work" />
                    </td>
                    <td>
                      <IndentedExcelText text={row.expected_result} indentLevel={0} />
                      <ModuleRowImageList images={row.images ?? []} placement="expected" />
                    </td>
                    {deviceHeaders.map((header) => {
                      const entry = getModuleDeviceEntry(row, header.slot_no);
                      return (
                        <Fragment key={"source-row-" + module.blueprint_item_id + "-" + row.module_row_id + "-" + header.slot_no}>
                          <td className="excel-center">{getModuleDeviceEntryValue(row, entry, "time_text")}</td>
                          <td>{getModuleDeviceEntryValue(row, entry, "window_text")}</td>
                          <td>{getModuleDeviceEntryValue(row, entry, "p_text")}</td>
                          <td className="excel-command-cell">{getModuleDeviceEntryValue(row, entry, "command_text")}</td>
                        </Fragment>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </article>
        );
      })}
    </section>
  );
}

function convertImportPreviewToModuleDetail(item: ModuleImportPreviewData): ModuleDetailData {
  return {
    module_id: 0,
    module_key: item.module_key ?? "preview",
    module_name: item.module_name,
    description: item.description,
    module_version_id: 0,
    version_no: 1,
    version_major: 0,
    version_minor: 0,
    version_label: "ver.0.0",
    status: "draft",
    status_label: "プレビュー",
    row_count: item.rows.length,
    source_xlsx_path: item.source_xlsx_path,
    created_by: item.created_by,
    header_time_text: item.header_time_text,
    target_text: item.target_text,
    common_p_text: item.common_p_text,
    target_device_text: item.target_device_text,
    device_headers: item.device_headers.map((header) => ({
      slot_no: header.slot_no,
      header_time_text: header.header_time_text,
      target_text: header.target_text,
      p_text: header.p_text,
      target_device_text: header.target_device_text,
    })),
    created_at: "-",
    updated_at: "-",
    rows: item.rows.map((row, index) => ({
      module_row_id: index + 1,
      row_order: row.row_order,
      row_type: row.row_type,
      major_no: row.major_no,
      middle_no: row.middle_no,
      minor_no: row.minor_no,
      tech_doc_text: row.tech_doc_text,
      work_text: row.work_text,
      indent_level: row.indent_level,
      expected_result: row.expected_result,
      time_text: row.time_text,
      window_text: row.window_text,
      p_text: row.p_text,
      command_text: row.command_text,
      note: row.note,
      device_entries: row.device_entries.map((entry) => ({
        slot_no: entry.slot_no,
        time_text: entry.time_text,
        window_text: entry.window_text,
        p_text: entry.p_text,
        command_text: entry.command_text,
      })),
      images: row.images ?? [],
    })),
  };
}

function getSourceDocModuleDeviceHeaders(item: SourceDocModuleItemData): ModuleDeviceHeaderData[] {
  const headersBySlot = new Map<number, ModuleDeviceHeaderData>();

  item.rows.forEach((row) => {
    row.device_entries.forEach((entry) => {
      if (!headersBySlot.has(entry.slot_no)) {
        headersBySlot.set(entry.slot_no, {
          slot_no: entry.slot_no,
          header_time_text: null,
          target_text: null,
          p_text: null,
          target_device_text: "device-" + String(entry.slot_no).padStart(2, "0"),
        });
      }
    });
  });

  if (headersBySlot.size === 0) {
    headersBySlot.set(1, {
      slot_no: 1,
      header_time_text: null,
      target_text: null,
      p_text: null,
      target_device_text: null,
    });
  }

  return [...headersBySlot.values()].sort((left, right) => left.slot_no - right.slot_no);
}

function getModuleDeviceHeaders(item: ModuleDetailData): ModuleDeviceHeaderData[] {
  const headersBySlot = new Map<number, ModuleDeviceHeaderData>();

  item.device_headers.forEach((header) => {
    headersBySlot.set(header.slot_no, header);
  });

  item.rows.forEach((row) => {
    row.device_entries.forEach((entry) => {
      if (!headersBySlot.has(entry.slot_no)) {
        headersBySlot.set(entry.slot_no, {
          slot_no: entry.slot_no,
          header_time_text: null,
          target_text: null,
          p_text: null,
          target_device_text: `device-${String(entry.slot_no).padStart(2, "0")}`,
        });
      }
    });
  });

  if (headersBySlot.size === 0) {
    headersBySlot.set(1, {
      slot_no: 1,
      header_time_text: item.header_time_text,
      target_text: item.target_text,
      p_text: item.common_p_text,
      target_device_text: item.target_device_text,
    });
  }

  return [...headersBySlot.values()].sort((left, right) => left.slot_no - right.slot_no);
}

function getModuleDeviceEntry(row: ModuleDetailRowData, slotNo: number): ModuleRowDeviceEntryData | null {
  if (row.device_entries.length > 0) {
    return row.device_entries.find((entry) => entry.slot_no === slotNo) ?? null;
  }

  if (slotNo !== 1) {
    return null;
  }

  return {
    slot_no: 1,
    time_text: row.time_text,
    window_text: row.window_text,
    p_text: row.p_text,
    command_text: row.command_text,
  };
}

type ModuleDeviceEntryValueKey = "time_text" | "window_text" | "p_text" | "command_text";

function getModuleDeviceEntryValue(
  row: ModuleDetailRowData,
  entry: ModuleRowDeviceEntryData | null,
  key: ModuleDeviceEntryValueKey,
): string {
  if (entry) {
    return entry[key] ?? "";
  }

  if (row.device_entries.length > 0) {
    return "";
  }

  return row[key] ?? "";
}

function buildIndentedRows(rows: ModuleDetailRowData[]): Array<{ row: ModuleDetailRowData; indentLevel: 0 | 1 | 2 | 3 | 4 }> {
  return rows.map((row) => {
    return { row, indentLevel: normalizeExcelIndentLevel(row.indent_level) };
  });
}

function normalizeExcelIndentLevel(
  indentLevel: number | null,
): 0 | 1 | 2 | 3 | 4 {
  if (indentLevel === null || Number.isNaN(indentLevel)) {
    return 0;
  }

  return Math.max(0, Math.min(Math.trunc(indentLevel), 4)) as 0 | 1 | 2 | 3 | 4;
}

function IndentedExcelText({
  text,
  indentLevel,
}: {
  text: string | null;
  indentLevel: 0 | 1 | 2 | 3 | 4;
}) {
  return (
    <div
      className={`excel-indent indent-level-${indentLevel}`}
      style={{ "--indent-offset": `${indentLevel * 18}px` } as CSSProperties}
    >
      <span className="excel-indent-guides" aria-hidden="true">
        <span className="excel-indent-slot" />
        <span className="excel-indent-slot" />
        <span className="excel-indent-slot" />
        <span className="excel-indent-slot" />
      </span>
      <span className="excel-indent-text">{text ?? ""}</span>
    </div>
  );
}



const caseDocText = {
  title: "案件化",
  description: "原本とAccess由来のマスタ値を紐づけ、案件CS生成に使う値を確認します。",
  sourceDoc: "原本",
  prefecture: "都道府県",
  building: "ビル",
  unitConfig: "ユニット構成",
  resolve: "解決値を確認",
  location: "設置場所",
  unit: "ユニット",
  targetDevice: "対象装置",
  none: "未選択",
  targetDeviceSlots: "対象装置番号対応表",
  excelNo: "target番号",
  hostAssignments: "ホスト割当",
  commonValues: "共通値",
  resolvedValues: "解決済み値",
  slot: "スロット",
  deviceType: "装置種別",
  system: "系",
  hostName: "ホスト名",
  key: "キー",
  value: "値",
  source: "出典",
  valueName: "値名",
  sourceTable: "出典テーブル",
  sourceColumn: "出典カラム",
  emptyTitle: "案件CS生成用の値を確認してください",
  loadingSourceDocs: "原本一覧を取得しています。",
  loadingPrefectures: "都道府県を取得しています。",
  loadingBuildings: "ビルを取得しています。",
  loadingUnitConfigs: "ユニット構成を取得しています。",
  selectLocation: "都道府県とビルを選択してください。",
  ready: "案件CS生成に使う値を確認できます。",
  sourceDocFailed: "原本一覧の取得に失敗しました。",
  sourceDocLoaded: "原本一覧を取得しました。",
  prefectureFailed: "都道府県の取得に失敗しました。",
  prefectureLoaded: "都道府県を取得しました。",
  selectPrefecture: "都道府県を選択してください。",
  buildingFailed: "ビルの取得に失敗しました。",
  buildingLoaded: "ビルを取得しました。",
  unitConfigFailed: "ユニット構成の取得に失敗しました。",
  unitConfigLoaded: "ユニット構成を取得しました。",
  apiFailed: "APIに接続できませんでした。",
  selectRequired: "原本、都道府県、ビル、ユニット構成を選択してください。",
  resolving: "案件CS生成用の値を解決しています。",
  resolveFailed: "値の解決に失敗しました。",
  resolved: "案件CS生成用の値を解決しました。",
  generate: "保存先を選んで案件CSを生成",
  generateStatus: "生成状態",
  generateReady: "解決値を確認後、案件CSを生成できます。",
  generateFirst: "先に解決値を確認してください。",
  generating: "案件CSを生成しています。",
  generated: "案件CSを生成しました。",
  generateFailed: "案件CSの生成に失敗しました。",
  saveDestinationCancelled: "保存先の選択をキャンセルしました。",
  saveDestinationFailed: "保存先の選択に失敗しました。",
  saveFailed: "案件CSの保存に失敗しました。",
  selectTargetRequired: "対象装置を1台以上選択してください。",
};

const caseDocPlaceholderText = {
  title: "プレースホルダ一覧",
  description: "案件CS生成で利用できるプレースホルダと参照元を確認します。",
  loading: "プレースホルダ定義を取得しています。",
  loaded: "プレースホルダ定義を取得しました。",
  failed: "プレースホルダ定義の取得に失敗しました。",
  apiFailed: "APIに接続できませんでした。",
  total: "定義数",
  visible: "表示件数",
  all: "すべて",
  enabled: "有効",
  disabled: "無効",
  deviceScoped: "装置別",
  commonScoped: "共通",
  name: "プレースホルダ",
  status: "状態",
  scope: "適用範囲",
  deviceType: "装置種別",
  sourceFile: "参照ファイル",
  keyColumn: "キー列",
  valueColumn: "値列",
  sourceColumn: "内部キー",
  keyValue: "共通キー",
  descriptionColumn: "説明",
  statusFilter: "状態で絞り込み",
  deviceTypeFilter: "装置種別で絞り込み",
  keyword: "キーワード検索",
  keywordPlaceholder: "名前、説明、参照元で検索",
  actions: "操作",
  add: "追加",
  edit: "編集",
  save: "保存",
  cancel: "キャンセル",
  enable: "有効化",
  disable: "無効化",
  editorCreateTitle: "プレースホルダを追加",
  editorEditTitle: "プレースホルダを編集",
  valueUnit: "値の単位",
  created: "プレースホルダを追加しました。",
  updated: "プレースホルダを更新しました。",
  statusUpdated: "プレースホルダの状態を更新しました。",
  saving: "プレースホルダを保存しています。",
  updatingStatus: "プレースホルダの状態を更新しています。",
  saveFailed: "プレースホルダの保存に失敗しました。",
  sourceColumnAutoHelp: "内部キーはプレースホルダ名と装置種別から自動生成されます。",
  mutationReady: "追加、編集、有効/無効切替を実行できます。",
  backToCaseDocs: "案件化へ戻る",
  emptyTitle: "プレースホルダ定義がありません",
  noMatchesTitle: "条件に一致する定義がありません",
};

function emptyCaseDocPlaceholderForm(): CaseDocPlaceholderFormState {
  return {
    name: "",
    enabled: false,
    scope: "device",
    device_type: "SBC",
    source_file: "",
    key_column: "",
    value_column: "",
    source_column: "",
    key_value: "",
    description: "",
  };
}

function toCaseDocPlaceholderForm(item: CaseDocPlaceholderMappingItemData): CaseDocPlaceholderFormState {
  return {
    name: item.name,
    enabled: item.enabled,
    scope: item.scope,
    device_type: item.device_type ?? "",
    source_file: item.source_file,
    key_column: item.key_column,
    value_column: item.value_column,
    source_column: item.source_column,
    key_value: item.key_value ?? "",
    description: item.description ?? "",
  };
}

function toGeneratedCaseDocPlaceholderSourceColumn(form: CaseDocPlaceholderFormState): string {
  const normalizedName = form.name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");
  const normalizedDeviceType = form.device_type
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");

  if (form.scope === "device" && normalizedDeviceType && normalizedName.startsWith(`${normalizedDeviceType}_`)) {
    return normalizedName.slice(normalizedDeviceType.length + 1) || normalizedName;
  }

  return normalizedName || "placeholder_value";
}
function toCaseDocPlaceholderPayload(form: CaseDocPlaceholderFormState): CaseDocPlaceholderMappingItemData {
  const scope = form.scope;
  return {
    name: form.name.trim(),
    enabled: form.enabled,
    scope,
    device_type: scope === "device" ? form.device_type.trim() || null : null,
    source_file: form.source_file.trim(),
    key_column: form.key_column.trim(),
    value_column: form.value_column.trim(),
    source_column: toGeneratedCaseDocPlaceholderSourceColumn(form),
    key_value: scope === "common" ? form.key_value.trim() || null : form.key_value.trim() || null,
    description: form.description.trim() || null,
  };
}

function CaseDocsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const requestedSourceDocId = searchParams.get("source_doc_id") ?? "";
  const currentUser = getStoredAuthUser();
  const [sourceDocListState, setSourceDocListState] = useState<SourceDocListState>({
    status: "loading",
    items: [],
    message: caseDocText.loadingSourceDocs,
  });
  const [prefectureState, setPrefectureState] = useState<CaseDocOptionLoadState>({
    status: "loading",
    items: [],
    message: caseDocText.loadingPrefectures,
  });
  const [buildingState, setBuildingState] = useState<CaseDocOptionLoadState>({
    status: "loading",
    items: [],
    message: caseDocText.loadingBuildings,
  });
  const [unitConfigState, setUnitConfigState] = useState<CaseDocUnitConfigLoadState>({
    status: "idle",
    items: [],
    message: caseDocText.selectLocation,
  });
  const [resolveState, setResolveState] = useState<CaseDocResolveState>({
    status: "idle",
    item: null,
    message: caseDocText.ready,
  });
  const [generateState, setGenerateState] = useState<CaseDocGenerateState>({
    status: "idle",
    filename: null,
    message: caseDocText.generateReady,
  });
  const [instanceCreateState, setInstanceCreateState] = useState<CaseDocGenerateState>({
    status: "idle",
    filename: null,
    message: "解決値を確認後、WebUI実行用の案件CSを保存できます。",
  });
  const [selectedSourceDocId, setSelectedSourceDocId] = useState("");
  const [selectedPrefecture, setSelectedPrefecture] = useState("");
  const [selectedBuilding, setSelectedBuilding] = useState("");
  const [selectedUnitConfigId, setSelectedUnitConfigId] = useState("");
  const [selectedTargetSlotKeys, setSelectedTargetSlotKeys] = useState<string[]>([]);

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchInitialOptions(): Promise<void> {
      try {
        const [sourceDocsResponse, prefecturesResponse] = await Promise.all([
          fetch(buildApiUrl("/api/v1/source-docs?status=published"), { signal: abortController.signal }),
          fetch(buildApiUrl("/api/v1/case-docs/master/prefectures"), { signal: abortController.signal }),
        ]);
        const sourceDocsBody = (await sourceDocsResponse.json()) as ApiResponse<SourceDocListData>;
        const prefecturesBody = (await prefecturesResponse.json()) as ApiResponse<CaseDocMasterOptionsData>;

        if (!sourceDocsResponse.ok || sourceDocsBody.result !== "success" || sourceDocsBody.data === null) {
          setSourceDocListState({ status: "unavailable", items: [], message: sourceDocsBody.message || caseDocText.sourceDocFailed });
        } else {
          setSourceDocListState({ status: "available", items: sourceDocsBody.data.items, message: caseDocText.sourceDocLoaded });
          const requestedSourceExists = sourceDocsBody.data.items.some(
            (item) => String(item.source_doc_id) === requestedSourceDocId,
          );
          setSelectedSourceDocId((currentValue) =>
            currentValue
            || (requestedSourceExists ? requestedSourceDocId : String(sourceDocsBody.data?.items[0]?.source_doc_id ?? "")),
          );
        }

        if (!prefecturesResponse.ok || prefecturesBody.result !== "success" || prefecturesBody.data === null) {
          setPrefectureState({ status: "unavailable", items: [], message: prefecturesBody.message || caseDocText.prefectureFailed });
        } else {
          setPrefectureState({ status: "available", items: prefecturesBody.data.items, message: caseDocText.prefectureLoaded });
          setSelectedPrefecture((currentValue) => currentValue || prefecturesBody.data?.items[0]?.value || "");
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setSourceDocListState({ status: "unavailable", items: [], message: caseDocText.apiFailed });
        setPrefectureState({ status: "unavailable", items: [], message: caseDocText.apiFailed });
      }
    }

    void fetchInitialOptions();

    return () => {
      abortController.abort();
    };
  }, [requestedSourceDocId]);

  useEffect(() => {
    if (!selectedPrefecture) {
      setBuildingState({ status: "available", items: [], message: caseDocText.selectPrefecture });
      setSelectedBuilding("");
      return;
    }

    const abortController = new AbortController();

    async function fetchBuildings(): Promise<void> {
      setBuildingState({ status: "loading", items: [], message: caseDocText.loadingBuildings });
      try {
        const endpoint = new URL(buildApiUrl("/api/v1/case-docs/master/buildings"), window.location.origin);
        endpoint.searchParams.set("prefecture", selectedPrefecture);
        const response = await fetch(endpoint.toString(), { signal: abortController.signal });
        const responseBody = (await response.json()) as ApiResponse<CaseDocMasterOptionsData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setBuildingState({ status: "unavailable", items: [], message: responseBody.message || caseDocText.buildingFailed });
          return;
        }

        setBuildingState({ status: "available", items: responseBody.data.items, message: caseDocText.buildingLoaded });
        setSelectedBuilding(responseBody.data.items[0]?.value ?? "");
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setBuildingState({ status: "unavailable", items: [], message: caseDocText.apiFailed });
      }
    }

    void fetchBuildings();

    return () => {
      abortController.abort();
    };
  }, [selectedPrefecture]);

  useEffect(() => {
    if (!selectedPrefecture || !selectedBuilding) {
      setUnitConfigState({ status: "idle", items: [], message: caseDocText.selectLocation });
      setSelectedUnitConfigId("");
      return;
    }

    const abortController = new AbortController();

    async function fetchUnitConfigs(): Promise<void> {
      setUnitConfigState({ status: "loading", items: [], message: caseDocText.loadingUnitConfigs });
      try {
        const endpoint = new URL(buildApiUrl("/api/v1/case-docs/master/unit-config"), window.location.origin);
        endpoint.searchParams.set("prefecture", selectedPrefecture);
        endpoint.searchParams.set("building", selectedBuilding);
        const response = await fetch(endpoint.toString(), { signal: abortController.signal });
        const responseBody = (await response.json()) as ApiResponse<CaseDocUnitConfigListData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setUnitConfigState({ status: "unavailable", items: [], message: responseBody.message || caseDocText.unitConfigFailed });
          return;
        }

        setUnitConfigState({ status: "available", items: responseBody.data.items, message: caseDocText.unitConfigLoaded });
        setSelectedUnitConfigId(responseBody.data.items[0]?.unit_config_id ?? "");
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setUnitConfigState({ status: "unavailable", items: [], message: caseDocText.apiFailed });
      }
    }

    void fetchUnitConfigs();

    return () => {
      abortController.abort();
    };
  }, [selectedPrefecture, selectedBuilding]);

  const selectedSourceDoc = sourceDocListState.items.find((item) => String(item.source_doc_id) === selectedSourceDocId) ?? null;
  const selectedUnitConfig = unitConfigState.items.find((item) => item.unit_config_id === selectedUnitConfigId) ?? null;
  const targetAssignmentOptions = resolveState.item?.host_assignments.filter((item) => item.device_type === "SBC") ?? [];
  const selectedTargetAssignments =
    selectedTargetSlotKeys.length > 0
      ? targetAssignmentOptions.filter((item) => selectedTargetSlotKeys.includes(item.slot_key))
      : resolveState.item?.target_assignments ?? [];
  const selectedTargetSummary =
    selectedTargetAssignments.length > 0
      ? selectedTargetAssignments.map((item) => item.host_name).join(" / ")
      : caseDocText.none;
  const selectedTargetDeviceSlots: CaseDocTargetDeviceSlotData[] = selectedTargetAssignments.map((item, index) => ({
    excel_no: index + 1,
    slot_key: item.slot_key,
    device_type: item.device_type,
    system: item.system,
    host_name: item.host_name,
  }));

  function toggleTargetSlotKey(slotKey: string): void {
    setSelectedTargetSlotKeys((current) =>
      current.includes(slotKey)
        ? current.filter((currentSlotKey) => currentSlotKey !== slotKey)
        : [...current, slotKey],
    );
  }

  async function handleResolveContext(): Promise<void> {
    if (!selectedSourceDocId || !selectedPrefecture || !selectedBuilding || !selectedUnitConfig) {
      setResolveState({ status: "error", item: null, message: caseDocText.selectRequired });
      return;
    }

    setResolveState({ status: "submitting", item: null, message: caseDocText.resolving });

    try {
      const response = await fetch(buildApiUrl("/api/v1/case-docs/resolve-context"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_doc_id: Number(selectedSourceDocId),
          prefecture: selectedPrefecture,
          building: selectedBuilding,
          fs_cluster_name: selectedUnitConfig.fs_cluster_name,
          block: selectedUnitConfig.block,
          unit_config_id: selectedUnitConfig.unit_config_id,
          target_slot_keys: selectedTargetSlotKeys.length > 0 ? selectedTargetSlotKeys : undefined,
        }),
      });
      const responseBody = (await response.json()) as ApiResponse<CaseDocResolveContextData>;

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setResolveState({ status: "error", item: null, message: responseBody.message || `${caseDocText.resolveFailed} HTTP ${response.status}` });
        return;
      }

      setResolveState({ status: "success", item: responseBody.data, message: caseDocText.resolved });
      setSelectedTargetSlotKeys(responseBody.data.target_assignments.map((item) => item.slot_key));
      setGenerateState({ status: "idle", filename: null, message: caseDocText.generateReady });
    } catch {
      setResolveState({ status: "error", item: null, message: caseDocText.apiFailed });
    }
  }


  async function handleGenerateCaseDoc(): Promise<void> {
    if (!selectedSourceDocId || !selectedPrefecture || !selectedBuilding || !selectedUnitConfig) {
      setGenerateState({ status: "error", filename: null, message: caseDocText.selectRequired });
      return;
    }

    if (!resolveState.item) {
      setGenerateState({ status: "error", filename: null, message: caseDocText.generateFirst });
      return;
    }

    if (selectedTargetSlotKeys.length === 0) {
      setGenerateState({ status: "error", filename: null, message: caseDocText.selectTargetRequired });
      return;
    }

    const suggestedFilename = `case-doc-${selectedSourceDocId}-${selectedUnitConfig.unit_config_id}.xlsm`;
    let saveSelection: CaseDocSaveSelection | null;
    try {
      saveSelection = await selectCaseDocSaveDestination(suggestedFilename);
    } catch {
      setGenerateState({ status: "error", filename: null, message: caseDocText.saveDestinationFailed });
      return;
    }

    if (saveSelection === null) {
      setGenerateState({ status: "idle", filename: null, message: caseDocText.saveDestinationCancelled });
      return;
    }

    setGenerateState({ status: "submitting", filename: null, message: caseDocText.generating });

    try {
      const response = await fetch(buildApiUrl("/api/v1/case-docs/generate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_doc_id: Number(selectedSourceDocId),
          prefecture: selectedPrefecture,
          building: selectedBuilding,
          fs_cluster_name: selectedUnitConfig.fs_cluster_name,
          block: selectedUnitConfig.block,
          unit_config_id: selectedUnitConfig.unit_config_id,
          target_slot_keys: selectedTargetSlotKeys,
        }),
      });

      if (!response.ok) {
        let message = `${caseDocText.generateFailed} HTTP ${response.status}`;
        try {
          const responseBody = (await response.json()) as ApiResponse<unknown>;
          message = responseBody.message || message;
        } catch {
          // Binary download endpoints may not always return JSON on failure.
        }
        setGenerateState({ status: "error", filename: null, message });
        return;
      }

      const blob = await response.blob();
      const contentDisposition = response.headers.get("Content-Disposition") ?? "";
      const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/);
      const filename = filenameMatch?.[1] ?? suggestedFilename;
      try {
        const savedFilename = await saveCaseDocBlob(blob, filename, saveSelection);
        setGenerateState({ status: "success", filename: savedFilename, message: `${caseDocText.generated} ${savedFilename}` });
      } catch {
        setGenerateState({ status: "error", filename: null, message: caseDocText.saveFailed });
      }
    } catch {
      setGenerateState({ status: "error", filename: null, message: caseDocText.apiFailed });
    }
  }

  async function handleCreateCaseDocInstance(): Promise<void> {
    if (!selectedSourceDocId || !selectedPrefecture || !selectedBuilding || !selectedUnitConfig || !resolveState.item) {
      setInstanceCreateState({ status: "error", filename: null, message: caseDocText.generateFirst });
      return;
    }
    if (selectedTargetSlotKeys.length === 0) {
      setInstanceCreateState({ status: "error", filename: null, message: caseDocText.selectTargetRequired });
      return;
    }

    setInstanceCreateState({ status: "submitting", filename: null, message: "案件CSを保存しています。" });
    try {
      const response = await fetch(buildApiUrl("/api/v1/case-docs/instances"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_doc_id: Number(selectedSourceDocId),
          prefecture: selectedPrefecture,
          building: selectedBuilding,
          fs_cluster_name: selectedUnitConfig.fs_cluster_name,
          block: selectedUnitConfig.block,
          unit_config_id: selectedUnitConfig.unit_config_id,
          target_slot_keys: selectedTargetSlotKeys,
          created_by: currentUser?.displayName ?? "WebUIユーザー",
        }),
      });
      const responseBody = await readApiResponse<CaseDocInstanceDetailData>(response);
      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setInstanceCreateState({
          status: "error",
          filename: null,
          message: responseBody.message || `案件CSの保存に失敗しました。HTTP ${response.status}`,
        });
        return;
      }
      setInstanceCreateState({
        status: "success",
        filename: responseBody.data.case_document_key,
        message: "WebUI実行用の案件CSを保存しました。",
      });
      navigate(`/case-docs/executions/${responseBody.data.case_document_id}`);
    } catch {
      setInstanceCreateState({ status: "error", filename: null, message: caseDocText.apiFailed });
    }
  }

  return (
    <Page title={caseDocText.title} description={caseDocText.description}>
      <section className="case-doc-panel">
        <form
          className="case-doc-form"
          onSubmit={(event) => {
            event.preventDefault();
            void handleResolveContext();
          }}
        >
          <label>
            {caseDocText.sourceDoc}
            <select value={selectedSourceDocId} onChange={(event) => setSelectedSourceDocId(event.target.value)}>
              {sourceDocListState.items.map((item) => (
                <option key={item.source_doc_id} value={item.source_doc_id}>
                  {item.source_doc_key} / {item.source_doc_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            {caseDocText.prefecture}
            <select value={selectedPrefecture} onChange={(event) => setSelectedPrefecture(event.target.value)}>
              {prefectureState.items.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <label>
            {caseDocText.building}
            <select value={selectedBuilding} onChange={(event) => setSelectedBuilding(event.target.value)}>
              {buildingState.items.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <label>
            {caseDocText.unitConfig}
            <select value={selectedUnitConfigId} onChange={(event) => setSelectedUnitConfigId(event.target.value)}>
              {unitConfigState.items.map((item) => (
                <option key={item.unit_config_id} value={item.unit_config_id}>
                  {item.fs_cluster_name} / {item.block}
                </option>
              ))}
            </select>
          </label>
          <button className="primary" type="submit" disabled={resolveState.status === "submitting"}>
            {caseDocText.resolve}
          </button>
        </form>
      </section>

      <section className={`list-status list-status-${resolveState.status === "error" ? "unavailable" : resolveState.status === "success" ? "available" : "loading"}`} aria-live="polite">
        <div>
          <span>{caseDocText.sourceDoc}</span>
          <strong>{selectedSourceDoc ? selectedSourceDoc.source_doc_key : caseDocText.none}</strong>
        </div>
        <div>
          <span>{caseDocText.location}</span>
          <strong>{selectedPrefecture && selectedBuilding ? `${selectedPrefecture} / ${selectedBuilding}` : caseDocText.none}</strong>
        </div>
        <div>
          <span>{caseDocText.unit}</span>
          <strong>{selectedUnitConfig ? `${selectedUnitConfig.fs_cluster_name} / ${selectedUnitConfig.block}` : caseDocText.none}</strong>
        </div>
        <div>
          <span>{caseDocText.targetDevice}</span>
          <strong>{selectedTargetSummary}</strong>
        </div>
        <p>{resolveState.message}</p>
      </section>

      {resolveState.item ? (
        <section className={`list-status list-status-${generateState.status === "error" ? "unavailable" : generateState.status === "success" ? "available" : "loading"} case-doc-generate-panel`} aria-live="polite">
          <div className="case-doc-target-select">
            <span>{caseDocText.targetDevice}</span>
            <div className="case-doc-target-options">
              {targetAssignmentOptions.map((item) => (
                <label key={item.slot_key} className="checkbox-field">
                  <input
                    type="checkbox"
                    checked={selectedTargetSlotKeys.includes(item.slot_key)}
                    onChange={() => toggleTargetSlotKey(item.slot_key)}
                  />
                  <span>{item.slot_key} / {item.host_name}</span>
                </label>
              ))}
            </div>
          </div>
          <div>
            <span>{caseDocText.generateStatus}</span>
            <strong>{generateState.filename ?? (generateState.status === "submitting" ? caseDocText.generating : caseDocText.generateReady)}</strong>
          </div>
          <p>{generateState.message}</p>
          <button className="primary" type="button" onClick={() => void handleGenerateCaseDoc()} disabled={generateState.status === "submitting"}>
            {caseDocText.generate}
          </button>
          <button
            className="secondary"
            type="button"
            onClick={() => void handleCreateCaseDocInstance()}
            disabled={instanceCreateState.status === "submitting"}
          >
            <span aria-hidden="true">✓</span>
            {instanceCreateState.status === "submitting" ? "保存中" : "WebUI実行用に保存"}
          </button>
          <p className={instanceCreateState.status === "error" ? "form-error" : ""}>{instanceCreateState.message}</p>
        </section>
      ) : null}

      {resolveState.item ? (
        <div className="case-doc-result-grid">
          <section className="section-band">
            <h2>{caseDocText.targetDeviceSlots}</h2>
            <DataTable
              columns={[caseDocText.excelNo, caseDocText.slot, caseDocText.deviceType, caseDocText.system, caseDocText.hostName]}
              rows={selectedTargetDeviceSlots.map((item) => [
                String(item.excel_no),
                item.slot_key,
                item.device_type,
                item.system ?? "-",
                item.host_name,
              ])}
            />
          </section>
          <section className="section-band">
            <h2>{caseDocText.hostAssignments}</h2>
            <DataTable
              columns={[caseDocText.slot, caseDocText.deviceType, caseDocText.system, caseDocText.hostName]}
              rows={resolveState.item.host_assignments.map((item) => [
                item.slot_key,
                item.device_type,
                item.system ?? "-",
                item.host_name,
              ])}
            />
          </section>
          <section className="section-band">
            <h2>{caseDocText.commonValues}</h2>
            <DataTable
              columns={[caseDocText.key, caseDocText.value, caseDocText.source]}
              rows={resolveState.item.common_values.map((item) => [item.key, item.value, item.source])}
            />
          </section>
          <section className="section-band case-doc-wide-section">
            <h2>{caseDocText.resolvedValues}</h2>
            <DataTable
              columns={[caseDocText.valueName, caseDocText.value, caseDocText.sourceTable, caseDocText.sourceColumn, caseDocText.hostName]}
              rows={resolveState.item.resolved_placeholders.map((item) => [
                item.placeholder,
                item.value,
                item.source_table,
                item.source_column,
                item.host_name ?? "-",
              ])}
            />
          </section>
        </div>
      ) : (
        <section className="empty-state">
          <h2>{caseDocText.emptyTitle}</h2>
          <p>{sourceDocListState.message} / {prefectureState.message} / {buildingState.message} / {unitConfigState.message}</p>
        </section>
      )}
    </Page>
  );
}

function formatCaseDocExecutionTime(value: string | null): string {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ja-JP", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(parsed);
}

function formatCaseDocExecutionUpdatedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(parsed);
}

function CaseDocExecutionTimeCell({
  item,
  disabled,
  busy,
  onUpdate,
}: {
  item: CaseDocExecutionItemData | undefined;
  disabled: boolean;
  busy: boolean;
  onUpdate: (item: CaseDocExecutionItemData, status: CaseDocExecutionStatus) => void;
}) {
  if (!item) {
    return <td className="excel-center case-execution-time-cell">-</td>;
  }

  if (item.status === "pending") {
    return (
      <td className="excel-center case-execution-time-cell case-execution-pending">
        <div className="case-execution-time-actions" aria-label="時刻欄の操作">
          <button
            type="button"
            className="case-execution-icon-button case-execution-check-button"
            title="チェックして現在時刻を記録"
            aria-label="チェックして現在時刻を記録"
            onClick={() => onUpdate(item, "checked")}
            disabled={disabled || busy}
          >
            ✓
          </button>
          <button
            type="button"
            className="case-execution-icon-button case-execution-skip-button"
            title="この項目をスキップ"
            aria-label="この項目をスキップ"
            onClick={() => onUpdate(item, "skipped")}
            disabled={disabled || busy}
          >
            −
          </button>
        </div>
      </td>
    );
  }

  return (
    <td className={`excel-center case-execution-time-cell case-execution-${item.status}`}>
      <span className="case-execution-time-value">
        {item.status === "checked" ? formatCaseDocExecutionTime(item.performed_at) : "SKIP"}
      </span>
      <button
        type="button"
        className="case-execution-reset-button"
        title="未実施へ戻す"
        aria-label="未実施へ戻す"
        onClick={() => onUpdate(item, "pending")}
        disabled={disabled || busy}
      >
        ↺
      </button>
    </td>
  );
}

function CaseDocExecutionPage() {
  const { caseDocumentId } = useParams<{ caseDocumentId: string }>();
  const navigate = useNavigate();
  const currentUser = getStoredAuthUser();
  const [instances, setInstances] = useState<CaseDocInstanceListItemData[]>([]);
  const [selectedId, setSelectedId] = useState(caseDocumentId ?? "");
  const [detail, setDetail] = useState<CaseDocInstanceDetailData | null>(null);
  const [listMessage, setListMessage] = useState("案件CS実行一覧を取得しています。");
  const [detailMessage, setDetailMessage] = useState("案件CSを選択してください。");
  const [mutatingItemId, setMutatingItemId] = useState<number | null>(null);
  const [isCompleting, setIsCompleting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [currentRowGroupIndex, setCurrentRowGroupIndex] = useState(0);

  useEffect(() => {
    const abortController = new AbortController();
    async function loadInstances(): Promise<void> {
      try {
        const response = await fetch(buildApiUrl("/api/v1/case-docs/instances"), { signal: abortController.signal });
        const responseBody = await readApiResponse<CaseDocInstanceListData>(response);
        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setListMessage(responseBody.message || "案件CS実行一覧の取得に失敗しました。");
          return;
        }
        const loadedInstances = responseBody.data.items;
        const activeInstances = loadedInstances.filter((instance) => instance.status === "active");
        const completedCount = loadedInstances.length - activeInstances.length;
        setInstances(loadedInstances);
        setListMessage(
          loadedInstances.length > 0
            ? `実施中 ${activeInstances.length}件、完了済み ${completedCount}件を取得しました。`
            : "保存済みの案件CSはありません。",
        );
        setSelectedId((current) => (
          activeInstances.some((instance) => String(instance.case_document_id) === current)
            ? current
            : String(activeInstances[0]?.case_document_id ?? "")
        ));
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setListMessage("APIに接続できませんでした。");
      }
    }
    void loadInstances();
    return () => abortController.abort();
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      setDetailMessage("案件CSを選択してください。");
      return;
    }
    const abortController = new AbortController();
    async function loadDetail(): Promise<void> {
      setDetailMessage("案件CS実行詳細を取得しています。");
      try {
        const response = await fetch(buildApiUrl(`/api/v1/case-docs/instances/${selectedId}`), { signal: abortController.signal });
        const responseBody = await readApiResponse<CaseDocInstanceDetailData>(response);
        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setDetail(null);
          setDetailMessage(responseBody.message || "案件CS実行詳細の取得に失敗しました。");
          return;
        }
        setDetail(responseBody.data);
        setCurrentRowGroupIndex(0);
        setDetailMessage("案件CS実行詳細を取得しました。");
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setDetail(null);
        setDetailMessage("APIに接続できませんでした。");
      }
    }
    void loadDetail();
    return () => abortController.abort();
  }, [selectedId]);

  useEffect(() => {
    const routeId = caseDocumentId ?? "";
    if (routeId === selectedId) {
      return;
    }
    navigate(selectedId ? `/case-docs/executions/${selectedId}` : "/case-docs/executions", { replace: true });
  }, [caseDocumentId, navigate, selectedId]);

  function selectInstance(nextId: string): void {
    setSelectedId(nextId);
    setCurrentRowGroupIndex(0);
    navigate(nextId ? `/case-docs/executions/${nextId}` : "/case-docs/executions", { replace: true });
  }

  async function updateExecutionItem(item: CaseDocExecutionItemData, status: CaseDocExecutionStatus): Promise<void> {
    if (!detail || detail.status === "completed") {
      return;
    }
    let skipReason: string | null = null;
    if (status === "skipped") {
      skipReason = window.prompt("スキップ理由を入力してください。空欄でも登録できます。", item.skip_reason ?? "");
      if (skipReason === null) {
        return;
      }
    }
    setMutatingItemId(item.execution_item_id);
    try {
      const response = await fetch(
        buildApiUrl(`/api/v1/case-docs/instances/${detail.case_document_id}/items/${item.execution_item_id}`),
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            status,
            performed_by: currentUser?.displayName ?? "WebUIユーザー",
            skip_reason: skipReason || null,
            expected_lock_version: item.lock_version,
          }),
        },
      );
      const responseBody = await readApiResponse<CaseDocInstanceDetailData>(response);
      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setDetailMessage(responseBody.message || "実施状態の更新に失敗しました。");
        return;
      }
      setDetail(responseBody.data);
      setDetailMessage("実施状態を更新しました。");
    } catch {
      setDetailMessage("APIに接続できませんでした。");
    } finally {
      setMutatingItemId(null);
    }
  }

  async function completeInstance(): Promise<void> {
    if (!detail || detail.pending_count > 0 || detail.status === "completed") {
      return;
    }
    setIsCompleting(true);
    try {
      const response = await fetch(buildApiUrl(`/api/v1/case-docs/instances/${detail.case_document_id}/complete`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ completed_by: currentUser?.displayName ?? "WebUIユーザー" }),
      });
      const responseBody = await readApiResponse<CaseDocInstanceDetailData>(response);
      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setDetailMessage(responseBody.message || "案件CSの完了に失敗しました。");
        return;
      }
      const completedInstance = responseBody.data;
      const nextActiveInstance = instances.find(
        (instance) => instance.status === "active" && instance.case_document_id !== completedInstance.case_document_id,
      );
      setInstances((current) => current.map((instance) => (
        instance.case_document_id === completedInstance.case_document_id ? completedInstance : instance
      )));
      setDetail(null);
      setListMessage("案件CSを完了し、完了済み一覧へ移動しました。");
      selectInstance(nextActiveInstance ? String(nextActiveInstance.case_document_id) : "");
    } catch {
      setDetailMessage("APIに接続できませんでした。");
    } finally {
      setIsCompleting(false);
    }
  }

  async function exportEvidence(): Promise<void> {
    if (!detail) {
      return;
    }
    setIsExporting(true);
    try {
      const response = await fetch(buildApiUrl(`/api/v1/case-docs/instances/${detail.case_document_id}/export`));
      if (!response.ok) {
        setDetailMessage(`証跡Excelの生成に失敗しました。HTTP ${response.status}`);
        return;
      }
      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `${detail.case_document_key}-evidence.xlsm`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
      setDetailMessage("証跡Excelをダウンロードしました。");
    } catch {
      setDetailMessage("APIに接続できませんでした。");
    } finally {
      setIsExporting(false);
    }
  }

  const rowOrders = detail
    ? [...new Set(detail.execution_items.map((item) => item.row_order))].sort((left, right) => left - right)
    : [];
  const rowGroups: Array<{ key: string; label: string; rowOrders: number[] }> = [];
  rowOrders.forEach((rowOrder) => {
    const baseItem = detail?.execution_items.find((item) => item.row_order === rowOrder);
    if (!baseItem) {
      return;
    }
    const minorNo = baseItem.minor_no?.trim() ?? "";
    if (minorNo || rowGroups.length === 0) {
      const numberLabel = [baseItem.major_no, baseItem.middle_no, baseItem.minor_no]
        .map((value) => value?.trim() ?? "")
        .filter(Boolean)
        .join(".");
      rowGroups.push({
        key: `row-group-${rowOrder}`,
        label: numberLabel || "番号なし",
        rowOrders: [],
      });
    }
    rowGroups[rowGroups.length - 1]?.rowOrders.push(rowOrder);
  });
  const effectiveRowGroupIndex = Math.min(currentRowGroupIndex, Math.max(rowGroups.length - 1, 0));
  const currentRowGroup = rowGroups[effectiveRowGroupIndex] ?? null;
  const visibleRowOrders = currentRowGroup?.rowOrders ?? [];
  const currentRowOrderSet = new Set(visibleRowOrders);
  const currentGroupItems = detail?.execution_items.filter((item) => currentRowOrderSet.has(item.row_order)) ?? [];
  const currentGroupCompletedCount = currentGroupItems.filter((item) => item.status !== "pending").length;
  const currentGroupPendingCount = currentGroupItems.length - currentGroupCompletedCount;
  const currentGroupHasPending = currentGroupPendingCount > 0;
  const activeInstances = instances.filter((instance) => instance.status === "active");
  const completedInstances = instances.filter((instance) => instance.status === "completed");
  return (
    <Page title="案件CS実行" description="案件CSの時刻欄をチェックまたはスキップし、実施証跡をExcelで出力します。">
      <section className="case-execution-selector section-band">
        <label>
          案件CS
          <select value={selectedId} onChange={(event) => selectInstance(event.target.value)}>
            <option value="">選択してください</option>
            {activeInstances.map((instance) => (
              <option key={instance.case_document_id} value={instance.case_document_id}>
                {instance.case_document_key} / {instance.source_doc_name}
              </option>
            ))}
          </select>
        </label>
        <p>{listMessage}</p>
      </section>

      <section className="section-band case-execution-completed-section">
        <div className="case-execution-completed-heading">
          <h2>完了済み案件CS</h2>
          <span>{completedInstances.length}件</span>
        </div>
        {completedInstances.length > 0 ? (
          <DataTable
            columns={["案件CS", "原本", "進捗", "作成者", "最終更新"]}
            rows={completedInstances.map((instance) => [
              instance.case_document_key,
              `${instance.source_doc_key} / ${instance.source_doc_name}`,
              `${instance.checked_count + instance.skipped_count} / ${instance.total_count}`,
              instance.created_by ?? "-",
              formatCaseDocExecutionUpdatedAt(instance.updated_at),
            ])}
          />
        ) : <p>完了済みの案件CSはありません。</p>}
      </section>

      {detail ? (
        <>
          <section className="case-execution-summary">
            <Fact label="案件CS" value={detail.case_document_key} />
            <Fact label="原本" value={`${detail.source_doc_key} / ${detail.source_doc_name}`} />
            <Fact label="進捗" value={`${detail.checked_count + detail.skipped_count} / ${detail.total_count}`} />
            <Fact label="状態" value={detail.status === "completed" ? "完了" : "実施中"} />
          </section>
          <section className="case-execution-toolbar section-band">
            <p aria-live="polite">{detailMessage}</p>
            <Toolbar>
              <button className="secondary" type="button" onClick={() => void exportEvidence()} disabled={isExporting}>
                <span aria-hidden="true">⇩</span>{isExporting ? "生成中" : "証跡Excel"}
              </button>
              <button
                className="primary"
                type="button"
                onClick={() => void completeInstance()}
                disabled={isCompleting || detail.pending_count > 0 || detail.status === "completed"}
              >
                <span aria-hidden="true">✓</span>{detail.status === "completed" ? "完了済み" : "案件CSを完了"}
              </button>
            </Toolbar>
          </section>

          <section className="section-band case-execution-grid-section">
            <div className="case-execution-sheet-heading">
              <div>
                <h2>案件CS</h2>
                <p>Excelプレビューと同じ列構成です。各targetの時刻欄からチェックまたはスキップを実行できます。</p>
              </div>
              <div className="case-execution-legend" aria-label="実施状態の凡例">
                <span><i className="case-execution-legend-pending" />未実施</span>
                <span><i className="case-execution-legend-checked" />チェック済み</span>
                <span><i className="case-execution-legend-skipped" />スキップ</span>
              </div>
            </div>
            <nav className="case-execution-step-pager" aria-label="小項番の表示切り替え">
              <button
                className="secondary"
                type="button"
                onClick={() => setCurrentRowGroupIndex((index) => Math.max(0, index - 1))}
                disabled={effectiveRowGroupIndex === 0}
              >
                <span aria-hidden="true">←</span>前へ
              </button>
              <div className="case-execution-step-current" aria-live="polite">
                <span>小項番</span>
                <strong>{currentRowGroup?.label ?? "-"}</strong>
                <span>{rowGroups.length > 0 ? `${effectiveRowGroupIndex + 1} / ${rowGroups.length}` : "0 / 0"}</span>
                <span>実施済み {currentGroupCompletedCount} / {currentGroupItems.length}</span>
                {currentGroupHasPending ? (
                  <span className="case-execution-step-validation" role="alert">
                    未入力 {currentGroupPendingCount}件: 次へ進むにはチェックまたはスキップを選択してください。
                  </span>
                ) : null}
              </div>
              <button
                className="secondary"
                type="button"
                onClick={() => setCurrentRowGroupIndex((index) => Math.min(rowGroups.length - 1, index + 1))}
                disabled={rowGroups.length === 0 || effectiveRowGroupIndex >= rowGroups.length - 1 || currentGroupHasPending}
              >
                次へ<span aria-hidden="true">→</span>
              </button>
            </nav>
            <div className="excel-sheet-wrap excel-sheet-wrap-case excel-sheet-scroll-with-sticky-left excel-sheet-scroll-case case-execution-table-wrap">
              <table className="excel-sheet excel-sheet-case excel-sheet-multi-device excel-sheet-sticky-left excel-sheet-case-sticky case-execution-sheet case-execution-sticky">
                <colgroup>
                  <col className="excel-col-small" />
                  <col className="excel-col-small" />
                  <col className="excel-col-small" />
                  <col className="excel-col-doc" />
                  <col className="excel-col-work-block" />
                  <col className="excel-col-work-block" />
                  <col className="excel-col-work-block" />
                  <col className="excel-col-work-block" />
                  <col className="excel-col-check" />
                  {detail.targets.map((target) => (
                    <Fragment key={`execution-cols-${target.excel_no}`}>
                      <col className="excel-col-time" />
                      <col className="excel-col-window" />
                      <col className="excel-col-prompt" />
                      <col className="excel-col-command" />
                    </Fragment>
                  ))}
                </colgroup>
                <tbody>
                  <tr className="excel-case-title-row">
                    <td colSpan={9} className="excel-case-title-cell">{detail.source_doc_name}</td>
                    {detail.targets.map((target, targetIndex) => {
                      const toneClass = targetIndex % 2 === 0 ? "excel-device-block-odd" : "excel-device-block-even";
                      return (
                        <Fragment key={`execution-top-label-${target.excel_no}`}>
                          <td className={`excel-case-top-label ${toneClass}`}>時刻</td>
                          <td className={`excel-case-top-label ${toneClass}`}>target</td>
                          <td className={`excel-case-top-label ${toneClass}`}>P</td>
                          <td className={`excel-case-top-label ${toneClass}`}>対象装置</td>
                        </Fragment>
                      );
                    })}
                  </tr>
                  <tr className="excel-case-device-meta-row">
                    <td colSpan={9} className="excel-case-left-blank" />
                    {detail.targets.map((target, targetIndex) => {
                      const toneClass = targetIndex % 2 === 0 ? "excel-device-block-odd" : "excel-device-block-even";
                      return (
                        <Fragment key={`execution-top-value-${target.excel_no}`}>
                          <td className={`excel-center ${toneClass}`} />
                          <td className={toneClass}>{target.excel_no}</td>
                          <td className={`excel-center ${toneClass}`} />
                          <td className={toneClass}>{target.host_name}</td>
                        </Fragment>
                      );
                    })}
                  </tr>
                  <tr className="excel-case-spacer-row">
                    <td colSpan={9 + detail.targets.length * 4} />
                  </tr>
                  <tr className="excel-case-group-row">
                    <td colSpan={3} className="excel-case-group-cell">通番</td>
                    <td className="excel-case-group-cell" />
                    <td colSpan={4} className="excel-case-group-cell">作業内容</td>
                    <td className="excel-case-group-cell" />
                    {detail.targets.map((target, targetIndex) => {
                      const toneClass = targetIndex % 2 === 0 ? "excel-device-block-odd" : "excel-device-block-even";
                      return (
                        <Fragment key={`execution-group-${target.excel_no}`}>
                          <td className={`excel-case-group-cell ${toneClass}`} />
                          <td className={`excel-case-group-cell ${toneClass}`} />
                          <td className={`excel-case-group-cell ${toneClass}`} />
                          <td className={`excel-case-device-name ${toneClass}`}>{target.host_name}</td>
                        </Fragment>
                      );
                    })}
                  </tr>
                  <tr>
                    <th>大</th>
                    <th>中</th>
                    <th>小</th>
                    <th>技術資料名</th>
                    <th colSpan={4}>作業内容</th>
                    <th>確認事項 or 項目</th>
                    {detail.targets.map((target, targetIndex) => {
                      const toneClass = targetIndex % 2 === 0 ? "excel-device-block-odd" : "excel-device-block-even";
                      return (
                        <Fragment key={`execution-header-${target.excel_no}`}>
                          <th className={toneClass}>時刻</th>
                          <th className={toneClass}>window</th>
                          <th className={toneClass}>P</th>
                          <th className={toneClass}>コマンド</th>
                        </Fragment>
                      );
                    })}
                  </tr>
                  {visibleRowOrders.map((rowOrder) => {
                    const rowItems = detail.execution_items.filter((item) => item.row_order === rowOrder);
                    const baseItem = rowItems[0];
                    if (!baseItem) {
                      return null;
                    }
                    return (
                      <tr key={rowOrder} className="excel-row">
                        <td className="excel-number">{baseItem.major_no ?? ""}</td>
                        <td className="excel-number">{baseItem.middle_no ?? ""}</td>
                        <td className="excel-number">{baseItem.minor_no ?? ""}</td>
                        <td>{baseItem.tech_doc_text ?? ""}</td>
                        <td colSpan={4} className="excel-work-cell excel-work-cell-wide">{baseItem.work_text ?? ""}</td>
                        <td>{baseItem.check_text ?? ""}</td>
                        {detail.targets.map((target) => {
                          const item = rowItems.find((candidate) => candidate.target_no === target.excel_no);
                          const isBusy = item ? mutatingItemId === item.execution_item_id : false;
                          return (
                            <Fragment key={`execution-row-${rowOrder}-${target.excel_no}`}>
                              <CaseDocExecutionTimeCell
                                item={item}
                                busy={isBusy}
                                disabled={detail.status === "completed"}
                                onUpdate={(targetItem, status) => void updateExecutionItem(targetItem, status)}
                              />
                              <td>{item?.window_text ?? ""}</td>
                              <td>{item?.p_text ?? ""}</td>
                              <td className="excel-command-cell">{item?.command_text ?? ""}</td>
                            </Fragment>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>

        </>
      ) : (
        <section className="empty-state">
          <h2>案件CSを選択してください</h2>
          <p>{detailMessage}</p>
        </section>
      )}
    </Page>
  );
}

function CaseDocPlaceholdersPage() {
  const currentUser = getStoredAuthUser();
  const [placeholderState, setPlaceholderState] = useState<CaseDocPlaceholderMappingListState>({
    status: "loading",
    items: [],
    message: caseDocPlaceholderText.loading,
  });
  const [statusFilter, setStatusFilter] = useState<CaseDocPlaceholderStatusFilter>("all");
  const [deviceTypeFilter, setDeviceTypeFilter] = useState("all");
  const [keywordFilter, setKeywordFilter] = useState("");
  const [reloadTick, setReloadTick] = useState(0);
  const [editorMode, setEditorMode] = useState<CaseDocPlaceholderEditorMode | null>(null);
  const [editingOriginalName, setEditingOriginalName] = useState<string | null>(null);
  const [formState, setFormState] = useState<CaseDocPlaceholderFormState>(() => emptyCaseDocPlaceholderForm());
  const [mutationState, setMutationState] = useState<CaseDocPlaceholderMutationState>({
    status: "idle",
    message: caseDocPlaceholderText.mutationReady,
  });

  useEffect(() => {
    if (currentUser?.role !== "admin") {
      return;
    }

    const abortController = new AbortController();

    async function fetchPlaceholders(): Promise<void> {
      setPlaceholderState({ status: "loading", items: [], message: caseDocPlaceholderText.loading });

      try {
        const response = await fetch(buildApiUrl("/api/v1/case-docs/placeholders"), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<CaseDocPlaceholderMappingListData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setPlaceholderState({
            status: "unavailable",
            items: [],
            message: responseBody.message || `${caseDocPlaceholderText.failed} HTTP ${response.status}`,
          });
          return;
        }

        setPlaceholderState({
          status: "available",
          items: responseBody.data.items,
          message: responseBody.message || caseDocPlaceholderText.loaded,
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setPlaceholderState({ status: "unavailable", items: [], message: caseDocPlaceholderText.apiFailed });
      }
    }

    void fetchPlaceholders();

    return () => {
      abortController.abort();
    };
  }, [currentUser?.role, reloadTick]);

  if (currentUser?.role !== "admin") {
    return (
      <Page title={caseDocPlaceholderText.title} description="この画面は管理者ユーザーのみ利用できます。">
        <section className="empty-state">
          <h2>表示権限がありません</h2>
          <p>プレースホルダ一覧は管理者ユーザーでログインした場合のみ表示できます。</p>
        </section>
      </Page>
    );
  }

  const enabledCount = placeholderState.items.filter((item) => item.enabled).length;
  const disabledCount = placeholderState.items.length - enabledCount;
  const deviceTypeOptions = Array.from(
    new Set(placeholderState.items.map((item) => item.device_type).filter((deviceType): deviceType is string => Boolean(deviceType))),
  ).sort((left, right) => left.localeCompare(right));
  const normalizedKeyword = keywordFilter.trim().toLocaleLowerCase();
  const generatedSourceColumn = toGeneratedCaseDocPlaceholderSourceColumn(formState);

  const filteredItems = placeholderState.items.filter((item) => {
    if (statusFilter === "enabled" && !item.enabled) {
      return false;
    }
    if (statusFilter === "disabled" && item.enabled) {
      return false;
    }
    if (deviceTypeFilter !== "all" && item.device_type !== deviceTypeFilter) {
      return false;
    }
    if (normalizedKeyword.length === 0) {
      return true;
    }

    const searchableText = [
      item.name,
      item.description,
      item.device_type,
      item.scope,
      item.source_file,
      item.key_column,
      item.value_column,
      item.source_column,
      item.key_value,
    ]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase();

    return searchableText.includes(normalizedKeyword);
  });

  function openCreateEditor(): void {
    setEditorMode("create");
    setEditingOriginalName(null);
    setFormState(emptyCaseDocPlaceholderForm());
    setMutationState({ status: "idle", message: caseDocPlaceholderText.mutationReady });
  }

  function openEditEditor(item: CaseDocPlaceholderMappingItemData): void {
    setEditorMode("edit");
    setEditingOriginalName(item.name);
    setFormState(toCaseDocPlaceholderForm(item));
    setMutationState({ status: "idle", message: caseDocPlaceholderText.mutationReady });
  }

  function closeEditor(): void {
    setEditorMode(null);
    setEditingOriginalName(null);
    setFormState(emptyCaseDocPlaceholderForm());
  }

  function updateFormField<TKey extends keyof CaseDocPlaceholderFormState>(key: TKey, value: CaseDocPlaceholderFormState[TKey]): void {
    setFormState((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmitPlaceholder(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (editorMode === null) {
      return;
    }

    setMutationState({ status: "submitting", message: caseDocPlaceholderText.saving });
    const payload = toCaseDocPlaceholderPayload(formState);
    const endpoint =
      editorMode === "create"
        ? buildApiUrl("/api/v1/case-docs/placeholders")
        : buildApiUrl(`/api/v1/case-docs/placeholders/${encodeURIComponent(editingOriginalName ?? payload.name)}`);
    const method = editorMode === "create" ? "POST" : "PUT";

    try {
      const response = await fetch(endpoint, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const responseBody = (await response.json()) as ApiResponse<CaseDocPlaceholderMappingItemData>;

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setMutationState({ status: "error", message: responseBody.message || `${caseDocPlaceholderText.saveFailed} HTTP ${response.status}` });
        return;
      }

      setMutationState({
        status: "success",
        message: editorMode === "create" ? caseDocPlaceholderText.created : caseDocPlaceholderText.updated,
      });
      closeEditor();
      setReloadTick((current) => current + 1);
    } catch {
      setMutationState({ status: "error", message: caseDocPlaceholderText.apiFailed });
    }
  }

  async function handleToggleEnabled(item: CaseDocPlaceholderMappingItemData): Promise<void> {
    setMutationState({ status: "submitting", message: caseDocPlaceholderText.updatingStatus });

    try {
      const response = await fetch(buildApiUrl(`/api/v1/case-docs/placeholders/${encodeURIComponent(item.name)}/enabled`), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !item.enabled }),
      });
      const responseBody = (await response.json()) as ApiResponse<CaseDocPlaceholderMappingItemData>;

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setMutationState({ status: "error", message: responseBody.message || `${caseDocPlaceholderText.saveFailed} HTTP ${response.status}` });
        return;
      }

      setMutationState({ status: "success", message: caseDocPlaceholderText.statusUpdated });
      setReloadTick((current) => current + 1);
    } catch {
      setMutationState({ status: "error", message: caseDocPlaceholderText.apiFailed });
    }
  }

  return (
    <Page title={caseDocPlaceholderText.title} description={caseDocPlaceholderText.description}>
      <Toolbar>
        <NavLink to="/case-docs" className="button-link">
          <span aria-hidden="true">{"←"}</span>
          {caseDocPlaceholderText.backToCaseDocs}
        </NavLink>
        <button className="primary" type="button" onClick={openCreateEditor}>
          <span aria-hidden="true">+</span>
          {caseDocPlaceholderText.add}
        </button>
      </Toolbar>

      <section className={`list-status list-status-${mutationState.status === "error" ? "unavailable" : mutationState.status === "success" ? "available" : placeholderState.status}`} aria-live="polite">
        <div>
          <span>{caseDocPlaceholderText.total}</span>
          <strong>{placeholderState.items.length}</strong>
        </div>
        <div>
          <span>{caseDocPlaceholderText.visible}</span>
          <strong>{filteredItems.length}</strong>
        </div>
        <div>
          <span>{caseDocPlaceholderText.enabled}</span>
          <strong>{enabledCount}</strong>
        </div>
        <div>
          <span>{caseDocPlaceholderText.disabled}</span>
          <strong>{disabledCount}</strong>
        </div>
        <p>{mutationState.status === "idle" ? placeholderState.message : mutationState.message}</p>
      </section>

      {placeholderState.items.length > 0 ? (
        <>
          <section className="placeholder-filter-panel" aria-label={caseDocPlaceholderText.title}>
            <label>
              {caseDocPlaceholderText.statusFilter}
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as CaseDocPlaceholderStatusFilter)}>
                <option value="all">{caseDocPlaceholderText.all}</option>
                <option value="enabled">{caseDocPlaceholderText.enabled}</option>
                <option value="disabled">{caseDocPlaceholderText.disabled}</option>
              </select>
            </label>
            <label>
              {caseDocPlaceholderText.deviceTypeFilter}
              <select value={deviceTypeFilter} onChange={(event) => setDeviceTypeFilter(event.target.value)}>
                <option value="all">{caseDocPlaceholderText.all}</option>
                {deviceTypeOptions.map((deviceType) => (
                  <option key={deviceType} value={deviceType}>{deviceType}</option>
                ))}
              </select>
            </label>
            <label>
              {caseDocPlaceholderText.keyword}
              <input
                value={keywordFilter}
                onChange={(event) => setKeywordFilter(event.target.value)}
                placeholder={caseDocPlaceholderText.keywordPlaceholder}
              />
            </label>
          </section>

          {filteredItems.length > 0 ? (
            <section className="section-band placeholder-list-section">
              <h2>{caseDocPlaceholderText.title}</h2>
              <DataTable
                columns={[
                  caseDocPlaceholderText.status,
                  caseDocPlaceholderText.name,
                  caseDocPlaceholderText.descriptionColumn,
                  caseDocPlaceholderText.deviceType,
                  caseDocPlaceholderText.scope,
                  caseDocPlaceholderText.sourceFile,
                  caseDocPlaceholderText.valueColumn,
                  caseDocPlaceholderText.keyColumn,
                  caseDocPlaceholderText.keyValue,
                  caseDocPlaceholderText.sourceColumn,
                  caseDocPlaceholderText.actions,
                ]}
                rows={filteredItems.map((item) => [
                  <span className={item.enabled ? "placeholder-state placeholder-state-enabled" : "placeholder-state placeholder-state-disabled"}>
                    {item.enabled ? caseDocPlaceholderText.enabled : caseDocPlaceholderText.disabled}
                  </span>,
                  <code>{item.name}</code>,
                  item.description ?? "-",
                  item.device_type ?? "-",
                  item.scope === "device" ? caseDocPlaceholderText.deviceScoped : caseDocPlaceholderText.commonScoped,
                  item.source_file,
                  item.value_column,
                  item.key_column,
                  item.key_value ?? "-",
                  item.source_column,
                  <div className="placeholder-row-actions">
                    <button className="secondary" type="button" onClick={() => openEditEditor(item)}>
                      {caseDocPlaceholderText.edit}
                    </button>
                    <button className="text-button" type="button" onClick={() => void handleToggleEnabled(item)} disabled={mutationState.status === "submitting"}>
                      {item.enabled ? caseDocPlaceholderText.disable : caseDocPlaceholderText.enable}
                    </button>
                  </div>,
                ])}
              />
            </section>
          ) : (
            <section className="empty-state">
              <h2>{caseDocPlaceholderText.noMatchesTitle}</h2>
              <p>{placeholderState.message}</p>
            </section>
          )}
        </>
      ) : (
        <section className="empty-state">
          <h2>{caseDocPlaceholderText.emptyTitle}</h2>
          <p>{placeholderState.message}</p>
        </section>
      )}

      {editorMode !== null ? (
        <div className="modal-backdrop" role="presentation">
          <section aria-labelledby="placeholder-editor-title" aria-modal="true" className="modal-dialog placeholder-editor-dialog" role="dialog">
            <h2 id="placeholder-editor-title">
              {editorMode === "create" ? caseDocPlaceholderText.editorCreateTitle : caseDocPlaceholderText.editorEditTitle}
            </h2>
            <form className="placeholder-editor-form" onSubmit={(event) => void handleSubmitPlaceholder(event)}>
              <label>
                {caseDocPlaceholderText.name}
                <input value={formState.name} onChange={(event) => updateFormField("name", event.target.value)} required pattern="[A-Z0-9_]+" />
              </label>
              <label className="checkbox-field placeholder-checkbox-field">
                {caseDocPlaceholderText.enabled}
                <input type="checkbox" checked={formState.enabled} onChange={(event) => updateFormField("enabled", event.target.checked)} />
              </label>
              <label>
                {caseDocPlaceholderText.valueUnit}
                <select value={formState.scope} onChange={(event) => updateFormField("scope", event.target.value as "device" | "common")}>
                  <option value="device">{caseDocPlaceholderText.deviceScoped}</option>
                  <option value="common">{caseDocPlaceholderText.commonScoped}</option>
                </select>
              </label>
              <label>
                {caseDocPlaceholderText.deviceType}
                <input value={formState.device_type} onChange={(event) => updateFormField("device_type", event.target.value)} disabled={formState.scope === "common"} />
              </label>
              <label>
                {caseDocPlaceholderText.sourceFile}
                <input value={formState.source_file} onChange={(event) => updateFormField("source_file", event.target.value)} required />
              </label>
              <label>
                {caseDocPlaceholderText.keyColumn}
                <input value={formState.key_column} onChange={(event) => updateFormField("key_column", event.target.value)} required />
              </label>
              <label>
                {caseDocPlaceholderText.valueColumn}
                <input value={formState.value_column} onChange={(event) => updateFormField("value_column", event.target.value)} required />
              </label>
              <label>
                {caseDocPlaceholderText.sourceColumn}
                <input value={generatedSourceColumn} readOnly />
                <span className="field-hint">{caseDocPlaceholderText.sourceColumnAutoHelp}</span>
              </label>
              <label>
                {caseDocPlaceholderText.keyValue}
                <input value={formState.key_value} onChange={(event) => updateFormField("key_value", event.target.value)} />
              </label>
              <label className="wide">
                {caseDocPlaceholderText.descriptionColumn}
                <textarea value={formState.description} onChange={(event) => updateFormField("description", event.target.value)} rows={3} />
              </label>
              {mutationState.status === "error" ? <p className="placeholder-editor-error">{mutationState.message}</p> : null}
              <div className="modal-actions wide">
                <button className="secondary" type="button" onClick={closeEditor}>
                  {caseDocPlaceholderText.cancel}
                </button>
                <button className="primary" type="submit" disabled={mutationState.status === "submitting"}>
                  {caseDocPlaceholderText.save}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </Page>
  );
}

function ModuleApprovalStatusPage() {
  const navigate = useNavigate();
  const [moduleListState, setModuleListState] = useState<ModuleListState>({
    status: "loading",
    items: [],
    message: "モジュール一覧を取得しています。",
  });
  const [selectedModuleVersionId, setSelectedModuleVersionId] = useState<number | null>(null);
  const [approvalDetailState, setApprovalDetailState] = useState<ApprovalStatusDetailState>({
    status: "idle",
    item: null,
    message: "対象モジュールを選ぶと承認状態の詳細を表示します。",
  });
  const [approvalMutationState, setApprovalMutationState] = useState<ApprovalStatusMutationState>({
    status: "idle",
    message: "実行できる操作を選ぶと状態変更APIを呼び出します。",
  });
  const currentUser = getStoredAuthUser();
  const approvalActor = currentUser?.displayName ?? "";
  const currentRoleLabel = currentUser ? getAuthRoleLabel(currentUser.role) : "未ログイン";
  const currentRoleDescription = currentUser ? getAuthRoleDescription(currentUser.role) : "ログインしてください。";
  const [approvalComment, setApprovalComment] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | ModuleApiStatus>("all");
  const [reloadTick, setReloadTick] = useState(0);
  const [isContentPreviewOpen, setIsContentPreviewOpen] = useState(false);

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchModules(): Promise<void> {
      setModuleListState({
        status: "loading",
        items: [],
        message: "モジュール一覧を取得しています。",
      });

      try {
        const response = await fetch(buildApiUrl("/api/v1/modules"), {
          signal: abortController.signal,
        });
        const responseBody = await readApiResponse<ModuleListData>(response);

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setModuleListState({
            status: "unavailable",
            items: [],
            message: responseBody.message || `モジュール一覧の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        const items = responseBody.data.items;
        setModuleListState({
          status: "available",
          items,
          message: responseBody.message || "モジュール一覧を取得しました。",
        });

        setSelectedModuleVersionId((current) => {
          if (items.length === 0) {
            return null;
          }
          if (current !== null && items.some((item) => item.module_version_id === current)) {
            return current;
          }
          return items[0].module_version_id;
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setModuleListState({
          status: "unavailable",
          items: [],
          message: "モジュール一覧の取得中にAPI接続で失敗しました。",
        });
      }
    }

    void fetchModules();

    return () => {
      abortController.abort();
    };
  }, [reloadTick]);

  const selectedSummary =
    moduleListState.items.find((item) => item.module_version_id === selectedModuleVersionId) ?? null;
  const moduleContentState = useModuleDetailState(
    selectedSummary ? String(selectedSummary.module_id) : undefined,
    selectedSummary ? String(selectedSummary.version_no) : null,
  );

  useEffect(() => {
    if (selectedSummary === null) {
      setApprovalDetailState({
        status: "idle",
        item: null,
        message: "対象モジュールを選ぶと承認状態の詳細を表示します。",
      });
      return;
    }

    const abortController = new AbortController();
    const targetModule = selectedSummary;

    async function fetchApprovalDetail(): Promise<void> {
      setApprovalDetailState({
        status: "loading",
        item: null,
        message: "モジュール承認状態の詳細を取得しています。",
      });

      try {
        const response = await fetch(
          buildApiUrl(`/api/v1/modules/${targetModule.module_id}/versions/${targetModule.version_no}/status`),
          { signal: abortController.signal },
        );
        const responseBody = await readApiResponse<ApprovalStatusDetailData>(response);

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setApprovalDetailState({
            status: "unavailable",
            item: null,
            message: responseBody.message || `モジュール承認状態詳細の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        setApprovalDetailState({
          status: "available",
          item: responseBody.data,
          message: responseBody.message || "モジュール承認状態の詳細を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setApprovalDetailState({
          status: "unavailable",
          item: null,
          message: "モジュール承認状態詳細の取得中にAPI接続で失敗しました。",
        });
      }
    }

    void fetchApprovalDetail();

    return () => {
      abortController.abort();
    };
  }, [selectedSummary?.module_id, selectedSummary?.version_no, reloadTick]);

  useEffect(() => {
    setApprovalMutationState({
      status: "idle",
      message: "実行できる操作を選ぶと状態変更APIを呼び出します。",
    });
    setApprovalComment("");
  }, [selectedModuleVersionId]);

  const selectedItem = approvalDetailState.item;
  const selectedExecutableTransitions = selectedItem?.allowed_transitions.filter((transition) =>
    canRunApprovalTransition(currentUser?.role, selectedItem.status, transition.to_status)
  ) ?? [];
  const canCommentOnSelectedApproval = selectedExecutableTransitions.length > 0;
  const selectedLatestReturnHistory = getLatestReturnHistory(selectedItem?.history);
  const statusFilterOptions: { value: "all" | ModuleApiStatus; label: string }[] = [
    { value: "all", label: "0. 全件表示" },
    { value: "draft", label: "1. 作成中" },
    { value: "review_requested", label: "2. 承認依頼中" },
    { value: "returned", label: "3. 差戻し" },
    { value: "published", label: "4. 承認済み" },
    { value: "archived", label: "5. 保管済み" },
  ];
  const filteredModuleItems = moduleListState.items.filter((item) =>
    statusFilter === "all" ? true : item.status === statusFilter,
  );

  function handleStatusFilterChange(nextFilter: "all" | ModuleApiStatus): void {
    setStatusFilter(nextFilter);
    const nextItems = moduleListState.items.filter((item) =>
      nextFilter === "all" ? true : item.status === nextFilter,
    );
    if (nextItems.length > 0) {
      setSelectedModuleVersionId(nextItems[0].module_version_id);
    }
  }

  async function handleApplyTransition(toStatus: ModuleApiStatus): Promise<void> {
    if (selectedSummary === null || selectedItem === null) {
      return;
    }

    if (!canRunApprovalTransition(currentUser?.role, selectedItem.status, toStatus)) {
      setApprovalMutationState({
        status: "error",
        message: "現在のユーザー権限では、この承認操作は実行できません。",
      });
      return;
    }

    const normalizedActor = approvalActor.trim();
    const normalizedComment = approvalComment.trim();
    if (normalizedActor.length === 0) {
      setApprovalMutationState({
        status: "error",
        message: "実行者を確認できません。ログインしてください。",
      });
      return;
    }
    if (isReturnTransition(selectedItem.status, toStatus) && normalizedComment.length === 0) {
      setApprovalMutationState({
        status: "error",
        message: returnReasonRequiredMessage,
      });
      return;
    }

    setApprovalMutationState({
      status: "submitting",
      message: "モジュール承認状態を変更しています。",
    });

    try {
      const response = await fetch(
        buildApiUrl(`/api/v1/modules/${selectedSummary.module_id}/versions/${selectedSummary.version_no}/status`),
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            status: toStatus,
            changed_by: normalizedActor,
            note: normalizedComment || undefined,
          }),
        },
      );
      const responseBody = await readApiResponse<ApprovalStatusDetailData>(response);

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setApprovalMutationState({
          status: "error",
          message: responseBody.message || `モジュール承認状態変更に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setApprovalDetailState({
        status: "available",
        item: responseBody.data,
        message: responseBody.message || "モジュール承認状態を更新しました。",
      });
      setApprovalMutationState({
        status: "success",
        message: responseBody.message || "モジュール承認状態を更新しました。",
      });
      setApprovalComment("");
      setModuleListState((current) => ({
        ...current,
        items: current.items.map((item) =>
          item.module_version_id === selectedSummary.module_version_id
            ? {
                ...item,
                status: responseBody.data!.status,
                status_label: responseBody.data!.status_label,
                version_no: responseBody.data!.version_no,
                version_major: responseBody.data!.version_major ?? item.version_major,
                version_minor: responseBody.data!.version_minor ?? item.version_minor,
                version_label: responseBody.data!.version_label ?? item.version_label,
              }
            : item,
        ),
      }));
      setReloadTick((current) => current + 1);
    } catch (error) {
      setApprovalMutationState({
        status: "error",
        message: "モジュール承認状態変更の実行中にAPI接続で失敗しました。",
      });
    }
  }

  const detailStatusClass =
    approvalDetailState.status === "idle" ? "loading" : approvalDetailState.status;
  const mutationStatusClass =
    approvalMutationState.status === "success"
      ? "available"
      : approvalMutationState.status === "error"
        ? "unavailable"
        : "loading";
  const showReturnReasonError =
    approvalMutationState.status === "error" && approvalMutationState.message === returnReasonRequiredMessage;

  return (
    <Page
      title="モジュール承認管理"
      description="モジュール版の承認状態を確認し、承認依頼・承認・差戻し・保管を行います。"
    >
      <section className="approval-flow approval-flow-with-heading" aria-label="モジュール承認状態フィルター">
        <div className="approval-filter-heading">
          <div>
            <span>承認対象</span>
            <h2>モジュールを選択</h2>
          </div>
          <strong>{filteredModuleItems.length} 件</strong>
        </div>
        {statusFilterOptions.map((option) => (
          <button
            key={option.value}
            className={option.value === statusFilter ? "approval-filter-button active" : "approval-filter-button"}
            type="button"
            onClick={() => handleStatusFilterChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </section>

      <section className={`list-status list-status-${moduleListState.status}`} aria-live="polite">
        <div>
          <span>一覧取得状態</span>
          <strong>
            {moduleListState.status === "loading"
              ? "取得中"
              : moduleListState.status === "available"
                ? "取得成功"
                : "取得失敗"}
          </strong>
        </div>
        <div>
          <span>対象件数</span>
          <strong>{filteredModuleItems.length}/{moduleListState.items.length}</strong>
        </div>
        <div>
          <span>選択中</span>
          <strong>{selectedSummary?.module_key ?? "未選択"}</strong>
        </div>
        <p>{moduleListState.message}</p>
      </section>

      {moduleListState.status === "available" && filteredModuleItems.length === 0 ? (
        <section className="empty-state">
          <h2>{moduleListState.items.length === 0 ? "モジュールはまだありません" : "条件に一致するモジュールはありません"}</h2>
          <p>
            {moduleListState.items.length === 0
              ? "モジュールを登録すると、この画面から承認状態と次の操作を確認できます。"
              : "フィルターを切り替えると、別の状態のモジュールを確認できます。"}
          </p>
        </section>
      ) : (
        <DataTable
          columns={["選択", "モジュールID", "モジュール名", "版", "承認状態", "次の操作", "作成者", "更新日", "タグ", "行数", "選択状態"]}
          rows={filteredModuleItems.map((item) => [
            <label className="approval-selection-radio">
              <input
                type="radio"
                name="module-approval-target"
                checked={selectedModuleVersionId === item.module_version_id}
                onChange={() => setSelectedModuleVersionId(item.module_version_id)}
                aria-label={`${item.module_key} ${formatVersionLabel(item)}を選択`}
              />
            </label>,
            <span className="approval-row-primary">{item.module_key}</span>,
            <span className="approval-row-primary">{item.module_name}</span>,
            <span className="approval-row-version">{formatVersionLabel(item)}</span>,
            <ModuleStatusPill status={item.status} label={item.status_label} />,
            selectedItem?.target_id === item.module_id && selectedItem.version_no === item.version_no
              ? selectedItem.next_action
              : "-",
            item.created_by ?? "-",
            item.updated_at,
            <ModuleFolderMembershipList item={item} />,
            String(item.row_count),
            selectedModuleVersionId === item.module_version_id ? (
              <span className="approval-selected-indicator"><span aria-hidden="true">✓</span>選択中</span>
            ) : (
              <button className="text-button" onClick={() => setSelectedModuleVersionId(item.module_version_id)}>
                選択
              </button>
            ),
          ])}
          rowClassNames={filteredModuleItems.map((item) =>
            selectedModuleVersionId === item.module_version_id ? "approval-row-selected" : undefined,
          )}
          rowAriaSelected={filteredModuleItems.map((item) => selectedModuleVersionId === item.module_version_id)}
        />
      )}

      <section
        className={`list-status list-status-${detailStatusClass} approval-current-selection ${selectedSummary ? "has-selection" : ""}`}
        aria-live="polite"
      >
        <div className="approval-current-selection-primary">
          <span>現在の選択</span>
          <strong>{selectedSummary ? `${selectedSummary.module_key} ${selectedSummary.module_name}` : "未選択"}</strong>
        </div>
        <div>
          <span>版 / 承認状態</span>
          <strong>
            {selectedSummary
              ? `${formatVersionLabel(selectedSummary)} / ${selectedSummary.status_label}`
              : "-"}
          </strong>
        </div>
        <div>
          <span>次の操作</span>
          <strong>{selectedItem?.next_action ?? "-"}</strong>
        </div>
        <p>{approvalDetailState.message}</p>
      </section>

      {selectedItem && selectedSummary ? (
        <ApprovalActionPanel
          idPrefix="module-approval-action"
          targetLabel={`${selectedSummary.module_key} ${selectedSummary.module_name}`}
          versionLabel={formatVersionLabel(selectedItem)}
          statusLabel={selectedItem.status_label}
          previewDisabled={moduleContentState.status !== "available" || moduleContentState.item === null}
          previewHint={
            moduleContentState.status === "available"
              ? "選択中のモジュール版を全画面で確認します。"
              : moduleContentState.message
          }
          onPreview={() => setIsContentPreviewOpen(true)}
          actor={approvalActor}
          roleLabel={currentRoleLabel}
          roleDescription={currentRoleDescription}
          canManage={canCommentOnSelectedApproval}
          isReviewRequested={selectedItem.status === "review_requested"}
          latestReturnNote={
            selectedItem.status === "returned"
              ? selectedLatestReturnHistory?.note ?? "コメントはありません。"
              : null
          }
          comment={approvalComment}
          onCommentChange={setApprovalComment}
          showReturnReasonError={showReturnReasonError}
          returnReasonMessage={returnReasonRequiredMessage}
          availableTransitionCount={selectedItem.allowed_transitions.length}
          executableTransitions={selectedExecutableTransitions}
          isSubmitting={approvalMutationState.status === "submitting"}
          onTransition={(toStatus) => void handleApplyTransition(toStatus)}
        />
      ) : null}

      {approvalMutationState.status !== "idle" && !showReturnReasonError ? (
        <section className={`approval-operation-feedback approval-operation-feedback-${mutationStatusClass}`} aria-live="polite">
          <strong>
            {approvalMutationState.status === "submitting"
              ? "変更中"
              : approvalMutationState.status === "success"
                ? "変更成功"
                : "変更失敗"}
          </strong>
          <span>{approvalMutationState.message}</span>
        </section>
      ) : null}

      {selectedItem && selectedSummary ? (
        <>
          <section className="detail-layout approval-target-detail">
            <div className="approval-target-detail-heading">
              <span>対象情報</span>
              <h2>モジュール</h2>
            </div>
            <div className="facts">
              <Fact label="モジュールID" value={selectedSummary.module_key} />
              <Fact label="モジュール名" value={selectedSummary.module_name} />
              <Fact label="版" value={formatVersionLabel(selectedItem)} />
              <Fact label="承認状態" value={selectedItem.status_label} />
              <Fact label="作成者" value={selectedSummary.created_by ?? "-"} />
              <Fact label="更新日" value={selectedSummary.updated_at} />
            </div>
            <div className="module-detail-note">
              <span>説明</span>
              <p>{selectedSummary.description ?? "説明は未設定です。"}</p>
              <span>先頭作業</span>
              <p>{selectedSummary.first_work_text ?? "先頭作業は未設定です。"}</p>
            </div>
          </section>

          <section className="section-band approval-related-panel">
            <h2>登録情報</h2>
            <div className="facts">
              <Fact label="取込元" value={selectedSummary.source_xlsx_path ?? "-"} />
              <Fact label="作成者" value={selectedSummary.created_by ?? "-"} />
              <Fact label="現在の版" value={formatVersionLabel(selectedItem)} />
              <Fact label="行数" value={String(selectedSummary.row_count)} />
            </div>
          </section>

          <ApprovalHistoryPanel
            key={`module-history-${selectedItem.target_id}-${selectedItem.version_no}`}
            history={selectedItem.history ?? []}
            noteLabel="コメント"
          />

          <Toolbar>
            <button className="secondary" onClick={() => navigate(`/modules/${selectedSummary.module_id}?version_no=${selectedSummary.version_no}`)}>
              <span aria-hidden="true">→</span>
              モジュール詳細へ
            </button>
          </Toolbar>
        </>
      ) : (
        <section className="empty-state">
          <h2>モジュールを選択してください</h2>
          <p>{approvalDetailState.message}</p>
        </section>
      )}

      {isContentPreviewOpen && moduleContentState.item ? (
        <PreviewOverlay
          title={`${moduleContentState.item.module_name.replace("_CS ", " ")} / 承認内容確認`}
          description="選択中のモジュール版を、承認画面から離れずに確認できます。"
          onClose={() => setIsContentPreviewOpen(false)}
        >
          <div className="preview-surface preview-surface-sheet">
            <ExcelModulePreview item={moduleContentState.item} mode="fullscreen" />
          </div>
        </PreviewOverlay>
      ) : null}
    </Page>
  );
}

function ApprovalPage() {
  const navigate = useNavigate();
  const [approvalListState, setApprovalListState] = useState<ApprovalStatusListState>({
    status: "loading",
    items: [],
    message: "承認状態一覧を取得しています。",
  });
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [approvalDetailState, setApprovalDetailState] = useState<ApprovalStatusDetailState>({
    status: "idle",
    item: null,
    message: "対象を選ぶと承認状態の詳細を表示します。",
  });
  const [approvalMutationState, setApprovalMutationState] = useState<ApprovalStatusMutationState>({
    status: "idle",
    message: "実行できる操作を選ぶと状態変更 API を呼び出します。",
  });
  const currentUser = getStoredAuthUser();
  const approvalActor = currentUser?.displayName ?? "";
  const currentRoleLabel = currentUser ? getAuthRoleLabel(currentUser.role) : "未ログイン";
  const currentRoleDescription = currentUser ? getAuthRoleDescription(currentUser.role) : "ログインしてください。";
  const [approvalComment, setApprovalComment] = useState("");
  const [approvalStatusFilter, setApprovalStatusFilter] = useState<"all" | ModuleApiStatus>("all");
  const [reloadTick, setReloadTick] = useState(0);
  const [isContentPreviewOpen, setIsContentPreviewOpen] = useState(false);

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchApprovalStatuses(): Promise<void> {
      setApprovalListState({
        status: "loading",
        items: [],
        message: "承認状態一覧を取得しています。",
      });

      try {
        const response = await fetch(buildApiUrl("/api/v1/statuses"), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<ApprovalStatusListData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setApprovalListState({
            status: "unavailable",
            items: [],
            message:
              responseBody.message || `承認状態一覧の取得に失敗しました。 HTTP ${response.status}`,
          });
          return;
        }

        const items = responseBody.data.items;
        setApprovalListState({
          status: "available",
          items,
          message: responseBody.message || "承認状態一覧を取得しました。",
        });

        setSelectedTargetId((current) => {
          if (items.length === 0) {
            return null;
          }
          if (current !== null && items.some((item) => item.target_id === current)) {
            return current;
          }
          return items[0].target_id;
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setApprovalListState({
          status: "unavailable",
          items: [],
          message: "承認状態一覧の取得中に API 接続で失敗しました。",
        });
      }
    }

    void fetchApprovalStatuses();

    return () => {
      abortController.abort();
    };
  }, [reloadTick]);

  useEffect(() => {
    if (selectedTargetId === null) {
      setApprovalDetailState({
        status: "idle",
        item: null,
        message: "対象を選ぶと承認状態の詳細を表示します。",
      });
      return;
    }

    const abortController = new AbortController();

    async function fetchApprovalDetail(): Promise<void> {
      setApprovalDetailState({
        status: "loading",
        item: null,
        message: "承認状態の詳細を取得しています。",
      });

      try {
        const response = await fetch(buildApiUrl(`/api/v1/statuses/${selectedTargetId}`), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<ApprovalStatusDetailData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setApprovalDetailState({
            status: "unavailable",
            item: null,
            message:
              responseBody.message || `承認状態詳細の取得に失敗しました。 HTTP ${response.status}`,
          });
          return;
        }

        setApprovalDetailState({
          status: "available",
          item: responseBody.data,
          message: responseBody.message || "承認状態の詳細を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setApprovalDetailState({
          status: "unavailable",
          item: null,
          message: "承認状態詳細の取得中に API 接続で失敗しました。",
        });
      }
    }

    void fetchApprovalDetail();

    return () => {
      abortController.abort();
    };
  }, [selectedTargetId, reloadTick]);

  useEffect(() => {
    setApprovalMutationState({
      status: "idle",
      message: "実行できる操作を選ぶと状態変更 API を呼び出します。",
    });
    setApprovalComment("");
    setIsContentPreviewOpen(false);
  }, [selectedTargetId]);

  const selectedItem = approvalDetailState.item;
  const selectedSummary =
    approvalListState.items.find((item) => item.target_id === selectedTargetId) ?? null;
  const sourceDocContentState = useSourceDocDetailState(
    selectedTargetId === null ? undefined : String(selectedTargetId),
  );
  const selectedExecutableTransitions = selectedItem?.allowed_transitions.filter((transition) =>
    canRunApprovalTransition(currentUser?.role, selectedItem.status, transition.to_status)
  ) ?? [];
  const canCommentOnSelectedApproval = selectedExecutableTransitions.length > 0;
  const selectedLatestReturnHistory = getLatestReturnHistory(selectedItem?.history);
  const approvalStatusFilterOptions: { value: "all" | ModuleApiStatus; label: string }[] = [
    { value: "all", label: "0. 全件表示" },
    { value: "draft", label: "1. 作成中" },
    { value: "review_requested", label: "2. 承認依頼中" },
    { value: "returned", label: "3. 差戻し" },
    { value: "published", label: "4. 承認済み" },
    { value: "archived", label: "5. 保管済み" },
  ];
  const filteredApprovalItems = approvalListState.items.filter((item) =>
    approvalStatusFilter === "all" ? true : item.status === approvalStatusFilter,
  );

  function handleApprovalStatusFilterChange(nextFilter: "all" | ModuleApiStatus): void {
    setApprovalStatusFilter(nextFilter);
    const nextItems = approvalListState.items.filter((item) =>
      nextFilter === "all" ? true : item.status === nextFilter,
    );
    if (nextItems.length > 0) {
      setSelectedTargetId(nextItems[0].target_id);
    }
  }

  async function handleApplyTransition(toStatus: ModuleApiStatus): Promise<void> {
    if (selectedItem === null) {
      return;
    }

    if (!canRunApprovalTransition(currentUser?.role, selectedItem.status, toStatus)) {
      setApprovalMutationState({
        status: "error",
        message: "現在のユーザー権限では、この承認操作は実行できません。",
      });
      return;
    }

    const normalizedActor = approvalActor.trim();
    const normalizedComment = approvalComment.trim();
    if (normalizedActor.length === 0) {
      setApprovalMutationState({
        status: "error",
        message: "実行者を入力してください。",
      });
      return;
    }
    if (isReturnTransition(selectedItem.status, toStatus) && normalizedComment.length === 0) {
      setApprovalMutationState({
        status: "error",
        message: returnReasonRequiredMessage,
      });
      return;
    }

    setApprovalMutationState({
      status: "submitting",
      message: "承認状態を変更しています。",
    });

    try {
      const response = await fetch(buildApiUrl(`/api/v1/statuses/${selectedItem.target_id}`), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          status: toStatus,
          changed_by: normalizedActor,
          note: normalizedComment || undefined,
        }),
      });
      const responseBody = (await response.json()) as ApiResponse<ApprovalStatusDetailData>;

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setApprovalMutationState({
          status: "error",
          message:
            responseBody.message || `承認状態変更に失敗しました。HTTP ${response.status}`,
        });
        return;
      }

      setApprovalDetailState({
        status: "available",
        item: responseBody.data,
        message: responseBody.message || "承認状態を更新しました。",
      });
      setApprovalMutationState({
        status: "success",
        message: responseBody.message || "承認状態を更新しました。",
      });
      setApprovalComment("");
      setReloadTick((current) => current + 1);
    } catch (error) {
      setApprovalMutationState({
        status: "error",
        message: "承認状態変更の実行中に API 接続で失敗しました。",
      });
    }
  }

  const detailStatusClass =
    approvalDetailState.status === "idle" ? "loading" : approvalDetailState.status;
  const mutationStatusClass =
    approvalMutationState.status === "success"
      ? "available"
      : approvalMutationState.status === "error"
        ? "unavailable"
        : "loading";
  const showReturnReasonError =
    approvalMutationState.status === "error" && approvalMutationState.message === returnReasonRequiredMessage;

  return (
    <Page
      title="原本承認管理"
      description="原本版の承認状態を確認し、承認依頼・承認・差戻し・保管を行います。"
    >
      <section className="approval-flow approval-flow-with-heading" aria-label="原本承認状態フィルター">
        <div className="approval-filter-heading">
          <div>
            <span>承認対象</span>
            <h2>原本を選択</h2>
          </div>
          <strong>{filteredApprovalItems.length} 件</strong>
        </div>
        {approvalStatusFilterOptions.map((option) => (
          <button
            key={option.value}
            className={option.value === approvalStatusFilter ? "approval-filter-button active" : "approval-filter-button"}
            type="button"
            onClick={() => handleApprovalStatusFilterChange(option.value)}
          >
            {option.label}
          </button>
        ))}
      </section>

      <section className={`list-status list-status-${approvalListState.status}`} aria-live="polite">
        <div>
          <span>一覧取得状態</span>
          <strong>
            {approvalListState.status === "loading"
              ? "取得中"
              : approvalListState.status === "available"
                ? "取得成功"
                : "取得失敗"}
          </strong>
        </div>
        <div>
          <span>対象件数</span>
          <strong>{filteredApprovalItems.length}/{approvalListState.items.length}</strong>
        </div>
        <div>
          <span>選択中</span>
          <strong>{selectedSummary?.target_key ?? "未選択"}</strong>
        </div>
        <p>{approvalListState.message}</p>
      </section>

      {approvalListState.status === "available" && filteredApprovalItems.length === 0 ? (
        <section className="empty-state">
          <h2>{approvalListState.items.length === 0 ? "原本はまだありません" : "条件に一致する原本はありません"}</h2>
          <p>
            {approvalListState.items.length === 0
              ? "原本を保存すると、この画面から承認状態と次の操作を確認できます。"
              : "フィルターを切り替えると、別の状態の原本を確認できます。"}
          </p>
        </section>
      ) : (
        <DataTable
          columns={["選択", "原本ID", "原本名", "版", "承認状態", "次の操作", "作成者", "更新日", "利用モジュール", "選択状態"]}
          rows={filteredApprovalItems.map((item) => [
            <label className="approval-selection-radio">
              <input
                type="radio"
                name="source-approval-target"
                checked={selectedTargetId === item.target_id}
                onChange={() => setSelectedTargetId(item.target_id)}
                aria-label={`${item.target_key} ${formatVersionLabel(item)}を選択`}
              />
            </label>,
            <span className="approval-row-primary">{item.target_key}</span>,
            <span className="approval-row-primary">{item.target_name}</span>,
            <span className="approval-row-version">{formatVersionLabel(item)}</span>,
            <ModuleStatusPill status={item.status} label={item.status_label} />,
            item.next_action,
            item.created_by ?? "-",
            item.updated_at,
            `${item.enabled_module_count}/${item.module_count}`,
            selectedTargetId === item.target_id ? (
              <span className="approval-selected-indicator"><span aria-hidden="true">✓</span>選択中</span>
            ) : (
              <button className="text-button" onClick={() => setSelectedTargetId(item.target_id)}>
                選択
              </button>
            ),
          ])}
          rowClassNames={filteredApprovalItems.map((item) =>
            selectedTargetId === item.target_id ? "approval-row-selected" : undefined,
          )}
          rowAriaSelected={filteredApprovalItems.map((item) => selectedTargetId === item.target_id)}
        />
      )}

      <section
        className={`list-status list-status-${detailStatusClass} approval-current-selection ${selectedSummary ? "has-selection" : ""}`}
        aria-live="polite"
      >
        <div className="approval-current-selection-primary">
          <span>現在の選択</span>
          <strong>{selectedSummary ? `${selectedSummary.target_key} ${selectedSummary.target_name}` : "未選択"}</strong>
        </div>
        <div>
          <span>版 / 承認状態</span>
          <strong>
            {selectedSummary
              ? `${formatVersionLabel(selectedSummary)} / ${selectedSummary.status_label}`
              : "-"}
          </strong>
        </div>
        <div>
          <span>次の操作</span>
          <strong>{selectedItem?.next_action ?? "-"}</strong>
        </div>
        <p>{approvalDetailState.message}</p>
      </section>

      {selectedItem ? (
        <ApprovalActionPanel
          idPrefix="source-approval-action"
          targetLabel={`${selectedItem.target_key} ${selectedItem.target_name}`}
          versionLabel={formatVersionLabel(selectedItem)}
          statusLabel={selectedItem.status_label}
          previewDisabled={sourceDocContentState.status !== "available" || sourceDocContentState.item === null}
          previewHint={
            sourceDocContentState.status === "available"
              ? "選択中の原本を全画面で確認します。"
              : sourceDocContentState.message
          }
          onPreview={() => setIsContentPreviewOpen(true)}
          actor={approvalActor}
          roleLabel={currentRoleLabel}
          roleDescription={currentRoleDescription}
          canManage={canCommentOnSelectedApproval}
          isReviewRequested={selectedItem.status === "review_requested"}
          latestReturnNote={
            selectedItem.status === "returned"
              ? selectedLatestReturnHistory?.note ?? "コメントはありません。"
              : null
          }
          comment={approvalComment}
          onCommentChange={setApprovalComment}
          showReturnReasonError={showReturnReasonError}
          returnReasonMessage={returnReasonRequiredMessage}
          availableTransitionCount={selectedItem.allowed_transitions.length}
          executableTransitions={selectedExecutableTransitions}
          isSubmitting={approvalMutationState.status === "submitting"}
          onTransition={(toStatus) => void handleApplyTransition(toStatus)}
        />
      ) : null}

      {approvalMutationState.status !== "idle" && !showReturnReasonError ? (
        <section className={`approval-operation-feedback approval-operation-feedback-${mutationStatusClass}`} aria-live="polite">
          <strong>
            {approvalMutationState.status === "submitting"
              ? "変更中"
              : approvalMutationState.status === "success"
                ? "変更成功"
                : "変更失敗"}
          </strong>
          <span>{approvalMutationState.message}</span>
        </section>
      ) : null}

      {selectedItem ? (
        <>
          <section className="detail-layout approval-target-detail">
            <div className="approval-target-detail-heading">
              <span>対象情報</span>
              <h2>原本</h2>
            </div>
            <div className="facts">
              <Fact label="原本ID" value={selectedItem.target_key} />
              <Fact label="原本名" value={selectedItem.target_name} />
              <Fact label="版" value={formatVersionLabel(selectedItem)} />
              <Fact label="承認状態" value={selectedItem.status_label} />
              <Fact label="作成者" value={selectedItem.created_by ?? "-"} />
              <Fact label="更新日" value={selectedItem.updated_at} />
            </div>
            <div className="module-detail-note">
              <span>説明</span>
              <p>{selectedItem.description ?? "説明は未設定です。"}</p>
              <span>変更メモ</span>
              <p>{selectedItem.change_note ?? "変更メモは未設定です。"}</p>
            </div>
          </section>

          <section className="section-band approval-related-panel">
            <h2>関連モジュール</h2>
            {selectedItem.module_names.length > 0 ? (
              <div className="approval-module-list">
                {selectedItem.module_names.map((moduleName) => (
                  <span key={moduleName} className="flow-step">
                    {moduleName}
                  </span>
                ))}
              </div>
            ) : (
              <p>関連モジュールはありません。</p>
            )}
          </section>

          <ApprovalHistoryPanel
            key={`source-history-${selectedItem.target_id}-${selectedItem.version_no}`}
            history={selectedItem.history ?? []}
            noteLabel="コメント"
          />

          <Toolbar>
            <button className="secondary" onClick={() => navigate(`/documents/${selectedItem.target_id}`)}>
              <span aria-hidden="true">→</span>
              原本詳細へ
            </button>
          </Toolbar>
        </>
      ) : (
        <section className="empty-state">
          <h2>承認対象を選択してください</h2>
          <p>{approvalDetailState.message}</p>
        </section>
      )}

      <section className="section-band">
        <h2>版管理ルール</h2>
        <p>
          M1 では最小ルールとして、メンバーが <code>draft</code> または <code>returned</code> から承認依頼を行い、
          承認者が <code>review_requested</code> を確認して承認または差戻しします。
          承認されたものは <code>published</code> へ移行し、最終的に <code>archived</code> へ保管します。
        </p>
      </section>

      {isContentPreviewOpen && sourceDocContentState.item ? (
        <PreviewOverlay
          title={`${sourceDocContentState.item.source_doc_name} / 承認内容確認`}
          description="選択中の原本を、承認画面から離れずに確認できます。"
          onClose={() => setIsContentPreviewOpen(false)}
        >
          <div className="preview-surface">
            <ExcelSourceDocPreview
              item={sourceDocContentState.item}
              onOpenModule={(moduleId) => navigate(`/modules/${moduleId}`)}
            />
          </div>
        </PreviewOverlay>
      ) : null}
    </Page>
  );
}

function Page({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">手順書DB / M1</p>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
      </header>
      {children}
    </div>
  );
}

function ActionCard({ title, body, to, action, icon }: { title: string; body: string; to: string; action: string; icon: string }) {
  return (
    <article className="action-card">
      <span className="card-icon" aria-hidden="true">{icon}</span>
      <h2>{title}</h2>
      <p>{body}</p>
      <NavLink to={to} className="button-link"><span aria-hidden="true">→</span>{action}</NavLink>
    </article>
  );
}

function WorkflowStageCard({
  step,
  title,
  count,
  unit,
  to,
  action,
}: {
  step: string;
  title: string;
  count: number;
  unit: string;
  to: string;
  action: string;
}) {
  return (
    <article className="workflow-stage-card">
      <span className="workflow-stage-number">{step}</span>
      <div>
        <h2>{title}</h2>
        <p><strong>{count}</strong>{unit}</p>
      </div>
      <NavLink to={to} className="workflow-stage-link">{action}<span aria-hidden="true">→</span></NavLink>
    </article>
  );
}

function WorkQueueCard({ title, count, to, action }: { title: string; count: number; to: string; action: string }) {
  return (
    <article className="work-queue-card">
      <div>
        <span>{title}</span>
        <strong>{count}<small>件</small></strong>
      </div>
      <NavLink to={to} className="text-button">{action}<span aria-hidden="true">→</span></NavLink>
    </article>
  );
}

function SearchForm({ fields, onSubmit }: { fields: [string, string][]; onSubmit: () => void }) {
  return (
    <form
      className="search-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      {fields.map(([label, value]) => (
        <label key={label}>
          {label}
          <input defaultValue={value} />
        </label>
      ))}
      <button className="primary" type="submit"><span aria-hidden="true">⌕</span>検索実行</button>
    </form>
  );
}

function ApprovalActionPanel({
  idPrefix,
  targetLabel,
  versionLabel,
  statusLabel,
  previewDisabled,
  previewHint,
  onPreview,
  actor,
  roleLabel,
  roleDescription,
  canManage,
  isReviewRequested,
  latestReturnNote,
  comment,
  onCommentChange,
  showReturnReasonError,
  returnReasonMessage,
  availableTransitionCount,
  executableTransitions,
  isSubmitting,
  onTransition,
}: {
  idPrefix: string;
  targetLabel: string;
  versionLabel: string;
  statusLabel: string;
  previewDisabled: boolean;
  previewHint: string;
  onPreview: () => void;
  actor: string;
  roleLabel: string;
  roleDescription: string;
  canManage: boolean;
  isReviewRequested: boolean;
  latestReturnNote: string | null;
  comment: string;
  onCommentChange: (comment: string) => void;
  showReturnReasonError: boolean;
  returnReasonMessage: string;
  availableTransitionCount: number;
  executableTransitions: ApprovalTransitionData[];
  isSubmitting: boolean;
  onTransition: (toStatus: ModuleApiStatus) => void;
}) {
  function handleTransition(transition: ApprovalTransitionData): void {
    const confirmed = window.confirm(
      `${targetLabel}\n「${transition.action_label}」を実行します。よろしいですか？`,
    );
    if (confirmed) {
      onTransition(transition.to_status);
    }
  }

  return (
    <section className="section-band approval-action-panel" aria-labelledby={`${idPrefix}-title`}>
      <div className="approval-action-header">
        <div className="approval-action-heading">
          <span>承認操作</span>
          <h2 id={`${idPrefix}-title`}>{targetLabel}</h2>
          <p>{versionLabel} / {statusLabel}</p>
          <button
            className="secondary approval-content-preview-button"
            type="button"
            onClick={onPreview}
            disabled={previewDisabled}
            title={previewHint}
          >
            <span aria-hidden="true">□</span>
            内容を確認
          </button>
        </div>
        <div className={`approval-permission-panel approval-permission-summary ${canManage ? "can-manage" : "view-only"}`}>
          <span>実行ユーザー</span>
          <strong>{actor || "未ログイン"} / {roleLabel}</strong>
          <p>{roleDescription}</p>
        </div>
      </div>

      {isReviewRequested ? (
        <div className="approval-lock-note">
          <strong>承認依頼中です</strong>
          <span>メンバー側では編集・再依頼操作を行わず、承認者の確認を待つ状態です。</span>
        </div>
      ) : null}

      {latestReturnNote !== null ? (
        <div className="approval-return-note">
          <strong>差戻しコメント</strong>
          <span>{latestReturnNote}</span>
        </div>
      ) : null}

      {canManage ? (
        <div className="approval-action-form">
          <label className="approval-comment-field">
            コメント
            <textarea
              value={comment}
              onChange={(event) => onCommentChange(event.target.value)}
              rows={3}
              placeholder="承認依頼の補足や差戻し理由を入力します。"
            />
          </label>
          {showReturnReasonError ? <p className="approval-inline-error">{returnReasonMessage}</p> : null}
          <div className="approval-action-buttons">
            {executableTransitions.map((transition) => (
              <button
                key={transition.to_status}
                className={
                  transition.to_status === "returned"
                    ? "approval-action-button approval-action-button-return"
                    : transition.to_status === "archived"
                      ? "secondary approval-action-button"
                      : "primary approval-action-button"
                }
                type="button"
                onClick={() => handleTransition(transition)}
                disabled={isSubmitting}
                title={transition.action_label}
              >
                <span aria-hidden="true">{transition.to_status === "returned" ? "↩" : "✓"}</span>
                {isSubmitting ? "変更中..." : transition.action_label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <p className="approval-role-note">
          {availableTransitionCount > 0
            ? "現在のユーザーでは、この状態に対して実行できる操作はありません。"
            : "この状態から実行できる承認操作はありません。"}
        </p>
      )}
    </section>
  );
}

function formatApprovalHistoryDateTime(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(parsed);
}

function ApprovalHistoryPanel({
  history,
  noteLabel,
}: {
  history: ApprovalStatusHistoryItemData[];
  noteLabel: string;
}) {
  const [showAll, setShowAll] = useState(false);
  const sortedHistory = [...history].sort((left, right) => {
    const leftTime = new Date(left.changed_at).getTime();
    const rightTime = new Date(right.changed_at).getTime();
    if (Number.isNaN(leftTime) || Number.isNaN(rightTime)) {
      return 0;
    }
    return rightTime - leftTime;
  });
  const visibleHistory = showAll ? sortedHistory : sortedHistory.slice(0, 5);

  return (
    <section className="section-band approval-history-panel">
      <div className="approval-history-heading">
        <div>
          <h2>承認履歴</h2>
          <p>最新の変更から表示します。</p>
        </div>
        <div className="approval-history-heading-actions">
          <strong>{sortedHistory.length} 件</strong>
          {sortedHistory.length > 5 ? (
            <button className="secondary" type="button" onClick={() => setShowAll((current) => !current)}>
              <span aria-hidden="true">{showAll ? "−" : "+"}</span>
              {showAll ? "最新5件に戻す" : "すべて表示"}
            </button>
          ) : null}
        </div>
      </div>
      {visibleHistory.length > 0 ? (
        <DataTable
          columns={["日時", "操作", "変更", "実行者", noteLabel]}
          rows={visibleHistory.map((item, index) => [
            <time dateTime={item.changed_at}>{formatApprovalHistoryDateTime(item.changed_at)}</time>,
            <span className="approval-history-action">
              {index === 0 ? <span className="approval-history-latest-label">最新</span> : null}
              {item.action_label}
            </span>,
            `${item.from_status_label ?? "-"} → ${item.to_status_label}`,
            item.changed_by ?? "-",
            item.note ?? "",
          ])}
          rowClassNames={visibleHistory.map((_, index) =>
            index === 0 ? "approval-history-row-latest" : undefined,
          )}
        />
      ) : (
        <p className="approval-history-empty">承認履歴はまだありません。</p>
      )}
    </section>
  );
}

function DataTable({
  columns,
  rows,
  rowClassNames,
  rowAriaSelected,
}: {
  columns: ReactNode[];
  rows: ReactNode[][];
  rowClassNames?: Array<string | undefined>;
  rowAriaSelected?: boolean[];
}) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((column, index) => <th key={index}>{column}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index} className={rowClassNames?.[index]} aria-selected={rowAriaSelected?.[index]}>
              {row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusPill({ status }: { status: Status }) {
  return <span className={`status status-${status}`}>{statusLabels[status]}</span>;
}

function ModuleStatusPill({ status, label }: { status: ModuleApiStatus; label: string }) {
  return <span className={`status status-module-${status}`}>{label}</span>;
}

function FlowStep({ label, active = false }: { label: string; active?: boolean }) {
  return <span className={active ? "flow-step active" : "flow-step"}>{label}</span>;
}

function Toolbar({ children }: { children: ReactNode }) {
  return <div className="toolbar">{children}</div>;
}

function FormGrid({ children }: { children: ReactNode }) {
  return <section className="form-grid">{children}</section>;
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function routeTitle(path: string) {
  const map: Record<string, string> = {
    "/home": "HOME画面",
    "/modules/search": "モジュール一覧",
    "/modules/list": "一覧 / 詳細",
    "/modules/register": "モジュール新規登録",
    "/modules/approval": "モジュール承認管理",
    "/documents/search": "原本一覧",
    "/documents/create": "原本新規作成 / 更新",
    "/case-docs": "新規案件化",
    "/case-docs/executions": "案件CS実行 / 完了",
    "/case-docs/placeholders": "プレースホルダ設定",
    "/approval": "原本承認管理",
  };
  if (path.startsWith("/modules/") && path !== "/modules/search" && path !== "/modules/list" && path !== "/modules/approval") {
    return "モジュール詳細";
  }
  if (path.startsWith("/case-docs/executions/")) {
    return "案件CS実行";
  }
  return map[path] ?? "一覧 / 詳細画面";
}


export default App;
