import { NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Fragment, useEffect, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";

type Status = "Draft" | "approval" | "archive";

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

type ModuleApiStatus = "draft" | "published" | "archived";

type ModuleListItemData = {
  module_id: number;
  module_key: string;
  module_name: string;
  description: string | null;
  module_version_id: number;
  version_no: number;
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
  message: string;
};

type ModuleDetailState = {
  status: "loading" | "available" | "unavailable";
  item: ModuleDetailData | null;
  message: string;
};

type ModuleCreateState = {
  status: "idle" | "submitting" | "success" | "error";
  item: ModuleDetailData | null;
  message: string;
};

type ModuleRegisterRowDraft = {
  rowId: number;
  indentLevel: number;
  majorNo: string;
  middleNo: string;
  minorNo: string;
  techDocText: string;
  workText: string;
  expectedResult: string;
  deviceEntries: ModuleRegisterDeviceEntryDraft[];
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

type ApprovalStatusListItemData = {
  target_id: number;
  target_key: string;
  target_name: string;
  target_type: "source-doc";
  version_no: number;
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

type ApprovalStatusDetailData = {
  target_id: number;
  target_key: string;
  target_name: string;
  target_type: "source-doc";
  version_no: number;
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

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const moduleStatusOptions: { value: "all" | ModuleApiStatus; label: string }[] = [
  { value: "all", label: "すべて" },
  { value: "draft", label: "作成中" },
  { value: "published", label: "承認済み" },
  { value: "archived", label: "保管済み" },
];

function buildApiUrl(path: string): string {
  if (API_BASE_URL) {
    return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
  }

  if (window.location.port === "5173") {
    return `http://localhost:8000${path}`;
  }

  return path;
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
        <Route path="/modules/:moduleId" element={<ModuleDetailPage />} />
        <Route path="/modules/register" element={<ModuleRegisterPage />} />
        <Route path="/documents/search" element={<DocumentSearchPage />} />
        <Route path="/documents/create" element={<DocumentEditPage />} />
        <Route path="/documents/:id" element={<DocumentDetailPage />} />
        <Route path="/approval" element={<ApprovalPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function Shell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isLogoutDialogOpen, setIsLogoutDialogOpen] = useState(false);

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
        <nav aria-label="主要メニュー">
          <NavItem to="/home" label="HOME" icon="⌂" />
          <NavItem to="/modules/search" label="モジュール検索" icon="⌕" />
          <NavItem to="/modules/register" label="モジュール登録" icon="⇧" />
          <NavItem to="/documents/search" label="原本参照" icon="▤" />
          <NavItem to="/documents/create" label="原本作成 / 更新" icon="✎" />
          <NavItem to="/approval" label="承認状態確認" icon="✓" />
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
                  navigate("/");
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

function NavItem({ to, label, icon }: { to: string; label: string; icon: string }) {
  return (
    <NavLink to={to} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
      <span aria-hidden="true">{icon}</span>
      {label}
    </NavLink>
  );
}

function LoginPage() {
  const navigate = useNavigate();
  return (
    <main className="login-screen">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-copy">
          <p className="eyebrow">Sprint 1 / SB1-04</p>
          <h1 id="login-title">手順書DB WebUI</h1>
          <p>モジュール登録、検索、原本作成、承認状態確認までの主要操作をWebUIから辿れるM1向け画面です。</p>
        </div>
        <form
          className="login-form"
          onSubmit={(event) => {
            event.preventDefault();
            navigate("/home");
          }}
        >
          <label>
            ユーザ名
            <input defaultValue="m1.user" autoComplete="username" />
          </label>
          <label>
            パスワード
            <input type="password" defaultValue="password" autoComplete="current-password" />
          </label>
          <button className="primary" type="submit">
            <span aria-hidden="true">→</span>
            ログイン
          </button>
        </form>
      </section>
    </main>
  );
}

function HomePage() {
  return (
    <Page title="HOME" description="画面遷移図の入口として、主要メニューと現在の作業状況を確認します。">
      <ApiHealthPanel />
      <section className="dashboard-grid" aria-label="主要操作">
        <ActionCard title="モジュール" body="検索、一覧確認、Excelファイル登録を行います。" to="/modules/search" action="検索へ" icon="⌕" />
        <ActionCard title="原本" body="モジュールを組み合わせて原本の作成、更新、参照を行います。" to="/documents/create" action="作成へ" icon="✎" />
        <ActionCard title="承認状態" body="Draft、承認待ち、保管済みの状態と版数を確認します。" to="/approval" action="確認へ" icon="✓" />
      </section>
      <section className="section-band">
        <h2>遷移サマリー</h2>
        <div className="flow-grid">
          <FlowStep label="ログイン" />
          <FlowStep label="HOME" />
          <FlowStep label="検索 / 登録" />
          <FlowStep label="一覧 / 詳細" />
          <FlowStep label="承認状態確認" />
        </div>
      </section>
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
  const [keyword, setKeyword] = useState("");
  const [status, setStatus] = useState<(typeof moduleStatusOptions)[number]["value"]>("all");

  function handleSubmit(): void {
    const params = new URLSearchParams();
    const normalizedKeyword = keyword.trim();

    if (normalizedKeyword) {
      params.set("keyword", normalizedKeyword);
    }

    if (status !== "all") {
      params.set("status", status);
    }

    const query = params.toString();
    navigate(query ? `/modules/list?${query}` : "/modules/list");
  }

  return (
    <Page title="モジュール検索" description="キーワードと承認状態で、登録済みモジュールを検索します。">
      <form
        className="search-form module-search-form"
        onSubmit={(event) => {
          event.preventDefault();
          handleSubmit();
        }}
      >
        <label>
          キーワード
          <input
            placeholder="例: 点検、交換、MOD-001"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
        </label>
        <label>
          承認状態
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value as (typeof moduleStatusOptions)[number]["value"])}
          >
            {moduleStatusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <button className="primary" type="submit">
          <span aria-hidden="true">⌕</span>
          検索
        </button>
      </form>
    </Page>
  );
}

function ModuleListPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const keyword = searchParams.get("keyword") ?? "";
  const statusFilter = searchParams.get("status") ?? "all";
  const [moduleListState, setModuleListState] = useState<ModuleListState>({
    status: "loading",
    items: [],
    message: "モジュール一覧を取得しています。",
  });

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchModules(): Promise<void> {
      setModuleListState({
        status: "loading",
        items: [],
        message: "モジュール一覧を取得しています。",
      });

      try {
        const endpoint = new URL(buildApiUrl("/api/v1/modules"), window.location.origin);

        if (keyword) {
          endpoint.searchParams.set("keyword", keyword);
        }

        if (statusFilter !== "all") {
          endpoint.searchParams.set("status", statusFilter);
        }

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
          message: responseBody.message || "モジュール一覧を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setModuleListState({
          status: "unavailable",
          items: [],
          message: "APIに接続できませんでした。",
        });
      }
    }

    void fetchModules();

    return () => {
      abortController.abort();
    };
  }, [keyword, statusFilter]);

  const statusFilterLabel =
    moduleStatusOptions.find((option) => option.value === statusFilter)?.label ?? statusFilter;

  return (
    <Page title="モジュール一覧" description="APIから取得したモジュール一覧と検索結果を確認します。">
      <section className={`list-status list-status-${moduleListState.status}`} aria-live="polite">
        <div>
          <span>取得状態</span>
          <strong>
            {moduleListState.status === "loading"
              ? "取得中"
              : moduleListState.status === "available"
                ? "取得完了"
                : "取得失敗"}
          </strong>
        </div>
        <div>
          <span>検索キーワード</span>
          <strong>{keyword || "指定なし"}</strong>
        </div>
        <div>
          <span>承認状態</span>
          <strong>{statusFilterLabel}</strong>
        </div>
        <p>{moduleListState.message}</p>
      </section>
      <Toolbar>
        <button className="secondary" onClick={() => navigate("/modules/search")}>
          <span aria-hidden="true">←</span>
          条件変更
        </button>
        <button className="primary" onClick={() => navigate("/documents/create")}>
          <span aria-hidden="true">＋</span>
          原本作成へ
        </button>
      </Toolbar>
      {moduleListState.status === "available" && moduleListState.items.length === 0 ? (
        <section className="empty-state">
          <h2>該当するモジュールはありません</h2>
          <p>検索条件を変えて再度確認してください。</p>
        </section>
      ) : (
        <DataTable
          columns={["モジュールID", "モジュール名", "版", "承認状態", "行数", "先頭作業", "作成者", "更新日", "操作"]}
          rows={moduleListState.items.map((item) => [
            item.module_key,
            item.module_name,
            `v${item.version_no}`,
            <ModuleStatusPill status={item.status} label={item.status_label} />,
            String(item.row_count),
            item.first_work_text ?? "-",
            item.created_by ?? "-",
            item.updated_at,
            <button className="text-button" onClick={() => navigate(`/modules/${item.module_id}`)}>詳細</button>,
          ])}
        />
      )}
    </Page>
  );
}

function ModuleDetailPage() {
  const navigate = useNavigate();
  const { moduleId } = useParams();
  const [moduleDetailState, setModuleDetailState] = useState<ModuleDetailState>({
    status: "loading",
    item: null,
    message: "モジュール詳細を取得しています。",
  });

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchModuleDetail(): Promise<void> {
      if (!moduleId) {
        setModuleDetailState({
          status: "unavailable",
          item: null,
          message: "モジュールIDが指定されていません。",
        });
        return;
      }

      setModuleDetailState({
        status: "loading",
        item: null,
        message: "モジュール詳細を取得しています。",
      });

      try {
        const response = await fetch(buildApiUrl(`/api/v1/modules/${moduleId}`), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<ModuleDetailData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
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
  }, [moduleId]);

  const item = moduleDetailState.item;

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
        <button className="primary" onClick={() => navigate("/documents/create")}>
          <span aria-hidden="true">＋</span>
          原本作成へ
        </button>
      </Toolbar>

      {item ? (
        <>
          <section className="detail-layout">
            <div className="facts">
              <Fact label="モジュールID" value={item.module_key} />
              <Fact label="モジュール名" value={item.module_name} />
              <Fact label="版" value={`v${item.version_no}`} />
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
          <ExcelModulePreview item={item} />
        </>
      ) : (
        <section className="empty-state">
          <h2>モジュール詳細を表示できません</h2>
          <p>{moduleDetailState.message}</p>
        </section>
      )}
    </Page>
  );
}

function ExcelModulePreview({ item }: { item: ModuleDetailData }) {
  const rowsWithIndent = buildIndentedRows(item.rows);
  const deviceHeaders = getModuleDeviceHeaders(item);

  return (
    <section className="excel-preview" aria-label="Excel-like module preview">
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
                </td>
                <td>{row.expected_result ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="excel-device-accordion-list">
        {deviceHeaders.map((header, index) => (
          <details key={header.slot_no} className="excel-device-accordion" open={index === 0}>
            <summary className="excel-device-accordion-summary">
              <div className="excel-device-accordion-title">
                <strong>{`装置 ${header.slot_no}`}</strong>
                <span>{header.target_device_text ?? `device-${String(header.slot_no).padStart(2, "0")}`}</span>
              </div>
              <div className="excel-device-accordion-meta">
                <span>{`時刻 ${header.header_time_text ?? "-"}`}</span>
                <span>{`target ${header.target_text ?? "-"}`}</span>
                <span>{`P ${header.p_text ?? "-"}`}</span>
              </div>
            </summary>

            <div className="excel-device-accordion-body">
              <div className="excel-sheet-wrap">
                <table className="excel-sheet excel-device-command-sheet">
                  <colgroup>
                    <col className="excel-col-small" />
                    <col className="excel-col-time" />
                    <col className="excel-col-window" />
                    <col className="excel-col-prompt" />
                    <col className="excel-col-command" />
                  </colgroup>
                  <thead>
                    <tr>
                      <th>行</th>
                      <th>時刻</th>
                      <th>window</th>
                      <th>P</th>
                      <th>コマンド</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rowsWithIndent.map(({ row }) => {
                      const entry = getModuleDeviceEntry(row, header.slot_no);

                      return (
                        <tr key={`${row.module_row_id}-${header.slot_no}`} className={`excel-row excel-row-${row.row_type}`}>
                          <td className="excel-number">{row.row_order}</td>
                          <td className="excel-center">{entry?.time_text ?? ""}</td>
                          <td>{entry?.window_text ?? ""}</td>
                          <td>{entry?.p_text ?? ""}</td>
                          <td className="excel-command-cell">{entry?.command_text ?? ""}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </details>
        ))}
      </div>

      <div className="excel-remarks">
        <strong>補足</strong>
        <p>共通の手順表を見せたまま、必要な装置のコマンド欄だけを開いて確認できます。装置台数が増えても比較しやすい表示です。</p>
      </div>
    </section>
  );
}

function ModuleSearchPageLegacy() {
  const navigate = useNavigate();
  return (
    <Page title="モジュール検索" description="検索条件を入力し、登録済みモジュールの一覧へ進みます。">
      <SearchForm
        fields={[
          ["キーワード", "初期点検"],
          ["カテゴリ", "点検"],
          ["ステータス", "Draft / 承認待ち / 保管済み"],
        ]}
        onSubmit={() => navigate("/modules/list")}
      />
    </Page>
  );
}

function ModuleListPageLegacy() {
  const navigate = useNavigate();
  return (
    <Page title="モジュール一覧" description="検索結果を確認し、原本作成や詳細確認の対象を選択します。">
      <Toolbar>
        <button className="secondary" onClick={() => navigate("/modules/search")}><span aria-hidden="true">←</span>条件変更</button>
        <button className="primary" onClick={() => navigate("/documents/create")}><span aria-hidden="true">＋</span>原本作成へ</button>
      </Toolbar>
      <DataTable
        columns={["ID", "モジュール名", "カテゴリ", "担当", "版数", "状態", "更新日", "操作"]}
        rows={modules.map((item) => [
          item.id,
          item.name,
          item.category,
          item.owner,
          item.version,
          <StatusPill status={item.status} />,
          item.updatedAt,
          <button className="text-button" onClick={() => navigate("/documents/create")}>選択</button>,
        ])}
      />
    </Page>
  );
}

function ModuleRegisterPageLegacy() {
  return (
    <Page title="モジュール登録" description="Excelファイルをドラッグ&ドロップし、登録実行までの流れを確認します。">
      <section className="upload-zone" aria-label="Excelファイル登録">
        <span className="upload-icon">⇧</span>
        <h2>Excelファイルをここへドロップ</h2>
        <p>登録API接続前の画面モックです。M1では操作導線と入力項目を確認します。</p>
        <button className="primary"><span aria-hidden="true">＋</span>ファイル選択</button>
      </section>
      <FormGrid>
        <label>モジュール名<input defaultValue="初期点検手順" /></label>
        <label>カテゴリ<input defaultValue="点検" /></label>
        <label>担当<input defaultValue="開発担当A" /></label>
        <label>備考<textarea defaultValue="Excelから構造データを取り込む想定" /></label>
      </FormGrid>
      <Toolbar>
        <button className="primary"><span aria-hidden="true">✓</span>登録実行</button>
      </Toolbar>
    </Page>
  );
}

function ModuleRegisterPage() {
  const navigate = useNavigate();
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
    },
  ]);
  const [createState, setCreateState] = useState<ModuleCreateState>({
    status: "idle",
    item: null,
    message: "装置ブロックと手順行を入力して、初版モジュールを保存してください。",
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
            work_text: row.workText.trim() || moduleNameInput.trim(),
            indent_level: row.indentLevel,
            expected_result: row.expectedResult.trim() || undefined,
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

      const responseBody = (await response.json()) as ApiResponse<ModuleDetailData>;

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

  const createdItem = createState.item;

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

      <form className="register-form" onSubmit={handleSubmit}>
        <FormGrid>
          <label>
            モジュールキー
            <input value={moduleKeyInput} onChange={(event) => setModuleKeyInput(event.target.value)} placeholder="MOD-004 未入力時は自動採番" />
          </label>
          <label>
            モジュール名
            <input value={moduleNameInput} onChange={(event) => setModuleNameInput(event.target.value)} required />
          </label>
          <label>
            作成者
            <input value={createdByInput} onChange={(event) => setCreatedByInput(event.target.value)} />
          </label>
          <label>
            取込元
            <input value={sourcePathInput} onChange={(event) => setSourcePathInput(event.target.value)} placeholder="imports/manual-module.xlsx" />
          </label>
          <label className="wide">
            説明
            <textarea value={descriptionInput} onChange={(event) => setDescriptionInput(event.target.value)} />
          </label>
        </FormGrid>

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
              <span>{`version ${createdItem.version_no}`}</span>
              <span>{createdItem.status_label}</span>
              <span>{`装置 ${createdItem.device_headers.length} 台`}</span>
            </div>
          ) : null}
        </section>

        <Toolbar>
          {createdItem ? (
            <button className="secondary" type="button" onClick={() => navigate(`/modules/${createdItem.module_id}`)}>
              <span aria-hidden="true">&lt;-</span>
              詳細を開く
            </button>
          ) : null}
          <button className="primary" type="submit" disabled={createState.status === "submitting"}>
            <span aria-hidden="true">save</span>
            {createState.status === "submitting" ? "保存中..." : "保存実行"}
          </button>
        </Toolbar>
      </form>
    </Page>
  );
}

function DocumentSearchPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialKeyword = searchParams.get("keyword") ?? "";
  const initialStatus = (searchParams.get("status") ?? "all") as (typeof moduleStatusOptions)[number]["value"];
  const [keywordInput, setKeywordInput] = useState(initialKeyword);
  const [statusInput, setStatusInput] = useState(initialStatus);
  const keyword = initialKeyword;
  const statusFilter = initialStatus;
  const [sourceDocListState, setSourceDocListState] = useState<SourceDocListState>({
    status: "loading",
    items: [],
    message: "原本一覧を取得しています。",
  });

  useEffect(() => {
    setKeywordInput(initialKeyword);
    setStatusInput(initialStatus);
  }, [initialKeyword, initialStatus]);

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchSourceDocs(): Promise<void> {
      setSourceDocListState({
        status: "loading",
        items: [],
        message: "原本一覧を取得しています。",
      });

      try {
        const endpoint = new URL(buildApiUrl("/api/v1/source-docs"), window.location.origin);

        if (keyword) {
          endpoint.searchParams.set("keyword", keyword);
        }

        if (statusFilter !== "all") {
          endpoint.searchParams.set("status", statusFilter);
        }

        const response = await fetch(endpoint.toString(), {
          signal: abortController.signal,
        });

        const responseBody = (await response.json()) as ApiResponse<SourceDocListData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
          setSourceDocListState({
            status: "unavailable",
            items: [],
            message: responseBody.message || `原本一覧の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        setSourceDocListState({
          status: "available",
          items: responseBody.data.items,
          message: responseBody.message || "原本一覧を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setSourceDocListState({
          status: "unavailable",
          items: [],
          message: "APIに接続できませんでした。",
        });
      }
    }

    void fetchSourceDocs();

    return () => {
      abortController.abort();
    };
  }, [keyword, statusFilter]);

  function handleSubmit(): void {
    const nextParams = new URLSearchParams();

    if (keywordInput.trim()) {
      nextParams.set("keyword", keywordInput.trim());
    }

    if (statusInput !== "all") {
      nextParams.set("status", statusInput);
    }

    const nextQuery = nextParams.toString();
    navigate(nextQuery ? `/documents/search?${nextQuery}` : "/documents/search");
  }

  const statusFilterLabel =
    moduleStatusOptions.find((option) => option.value === statusFilter)?.label ?? statusFilter;

  return (
    <Page title="原本参照" description="APIから取得した原本一覧を確認し、関連モジュールと詳細情報を追えます。">
      <form
        className="search-form module-search-form"
        onSubmit={(event) => {
          event.preventDefault();
          handleSubmit();
        }}
      >
        <label>
          キーワード
          <input
            placeholder="例: M1確認用 / MOD-001 / 原本A"
            value={keywordInput}
            onChange={(event) => setKeywordInput(event.target.value)}
          />
        </label>
        <label>
          状態
          <select
            value={statusInput}
            onChange={(event) => setStatusInput(event.target.value as (typeof moduleStatusOptions)[number]["value"])}
          >
            {moduleStatusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <button className="primary" type="submit">
          <span aria-hidden="true">⌕</span>
          検索
        </button>
      </form>

      <section className={`list-status list-status-${sourceDocListState.status}`} aria-live="polite">
        <div>
          <span>取得状態</span>
          <strong>
            {sourceDocListState.status === "loading"
              ? "取得中"
              : sourceDocListState.status === "available"
                ? "取得成功"
                : "取得失敗"}
          </strong>
        </div>
        <div>
          <span>検索キーワード</span>
          <strong>{keyword || "指定なし"}</strong>
        </div>
        <div>
          <span>状態</span>
          <strong>{statusFilterLabel}</strong>
        </div>
        <p>{sourceDocListState.message}</p>
      </section>
      <Toolbar>
        <button className="secondary" onClick={() => navigate("/documents/search")}>
          <span aria-hidden="true">↺</span>
          条件を戻す
        </button>
        <button className="primary" onClick={() => navigate("/documents/create")}>
          <span aria-hidden="true">＋</span>
          原本作成へ
        </button>
      </Toolbar>
      {sourceDocListState.status === "available" && sourceDocListState.items.length === 0 ? (
        <section className="empty-state">
          <h2>該当する原本はありません</h2>
          <p>検索条件を変えて再度確認してください。</p>
        </section>
      ) : (
        <DataTable
          columns={["原本ID", "原本名", "版", "状態", "利用モジュール", "有効数", "作成者", "更新日", "操作"]}
          rows={sourceDocListState.items.map((item) => [
            item.source_doc_key,
            item.source_doc_name,
            `v${item.version_no}`,
            <ModuleStatusPill status={item.status} label={item.status_label} />,
            item.module_names.join(", ") || "-",
            `${item.enabled_module_count}/${item.module_count}`,
            item.created_by ?? "-",
            item.updated_at,
            <button className="text-button" onClick={() => navigate(`/documents/${item.source_doc_id}`)}>詳細</button>,
          ])}
        />
      )}
    </Page>
  );
}

function LegacyDocumentEditPage() {
  const navigate = useNavigate();
  const [sourceDocKeyInput, setSourceDocKeyInput] = useState("");
  const [sourceDocNameInput, setSourceDocNameInput] = useState("M1 procedure bundle");
  const [descriptionInput, setDescriptionInput] = useState("Created from source document register screen.");
  const [changeNoteInput, setChangeNoteInput] = useState("Initial draft");
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
        const response = await fetch(buildApiUrl("/api/v1/modules"), {
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
          message: responseBody.message || "利用可能なモジュールを取得しました。",
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
              placeholder="BP-STD-003 auto-generated when blank"
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
              <span>version {createdItem.version_no}</span>
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
  const isEditMode = editSourceDocId !== null;
  const [sourceDocKeyInput, setSourceDocKeyInput] = useState("");
  const [sourceDocNameInput, setSourceDocNameInput] = useState("M1 procedure bundle");
  const [descriptionInput, setDescriptionInput] = useState("Created from source document register screen.");
  const [changeNoteInput, setChangeNoteInput] = useState("Initial draft");
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
  const [items, setItems] = useState<SourceDocCreateItemDraft[]>([{ rowId: 1, moduleId: "", enabled: true }]);
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
        const response = await fetch(buildApiUrl("/api/v1/modules"), {
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
          message: responseBody.message || "Modules are available.",
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
        setChangeNoteInput(detail.change_note ?? "Updated draft");
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
          message: `${responseBody.data.source_doc_key} を更新しました。現在は version ${responseBody.data.version_no} です。`,
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
              placeholder="BP-STD-003 auto-generated when blank"
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
              <span>version {createdItem.version_no}</span>
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

function DocumentDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [sourceDocDetailState, setSourceDocDetailState] = useState<SourceDocDetailState>({
    status: "loading",
    item: null,
    message: "原本詳細を取得しています。",
  });

  useEffect(() => {
    const abortController = new AbortController();

    async function fetchSourceDocDetail(): Promise<void> {
      setSourceDocDetailState({
        status: "loading",
        item: null,
        message: "原本詳細を取得しています。",
      });

      try {
        const response = await fetch(buildApiUrl(`/api/v1/source-docs/${id}`), {
          signal: abortController.signal,
        });
        const responseBody = (await response.json()) as ApiResponse<SourceDocDetailData>;

        if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
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

  const item = sourceDocDetailState.item;

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
        <button className="secondary" onClick={() => navigate("/documents/search")}><span aria-hidden="true">↩</span>一覧へ戻る</button>
        <button
          className="primary"
          onClick={() => {
            if (item) {
              navigate(`/documents/create?id=${item.source_doc_id}`);
            }
          }}
        ><span aria-hidden="true">✎</span>更新する</button>
      </Toolbar>
      {item ? (
        <>
          <section className="detail-layout">
            <div className="facts">
              <Fact label="原本ID" value={item.source_doc_key} />
              <Fact label="原本名" value={item.source_doc_name} />
              <Fact label="版" value={`v${item.version_no}`} />
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
          <ExcelSourceDocPreview item={item} onOpenModule={(moduleId) => navigate(`/modules/${moduleId}`)} />
        </>
      ) : (
        <section className="empty-state">
          <h2>原本詳細を表示できません</h2>
          <p>{sourceDocDetailState.message}</p>
        </section>
      )}
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
        <div className="excel-cell excel-sequence-cell">{`v${item.version_no}`}</div>
        <div className="excel-cell excel-target-value">{item.status_label}</div>
        <div className="excel-cell excel-target-value">{`${item.enabled_module_count}/${item.module_count}`}</div>
        <div className="excel-cell excel-device-value">{moduleNames.join(", ") || "-"}</div>
      </div>

      {item.items.map((module) => (
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

          <div className="excel-sheet-wrap">
            <table className="excel-sheet">
              <colgroup>
                <col className="excel-col-small" />
                <col className="excel-col-small" />
                <col className="excel-col-small" />
                <col className="excel-col-doc" />
                <col className="excel-col-work" />
                <col className="excel-col-check" />
                <col className="excel-col-time" />
                <col className="excel-col-window" />
                <col className="excel-col-prompt" />
                <col className="excel-col-command" />
              </colgroup>
              <thead>
                <tr>
                  <th>大</th>
                  <th>中</th>
                  <th>小</th>
                  <th>技術資料名</th>
                  <th>作業内容</th>
                  <th>確認事項 or 項目</th>
                  <th>時刻</th>
                  <th>window</th>
                  <th>P</th>
                  <th>コマンド</th>
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
                    </td>
                    <td>{row.expected_result ?? ""}</td>
                    <td className="excel-center">{row.time_text ?? ""}</td>
                    <td>{row.window_text ?? ""}</td>
                    <td>{row.p_text ?? ""}</td>
                    <td className="excel-command-cell">{row.command_text ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ))}
    </section>
  );
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
    message: "対象を選択すると承認状態の詳細を表示します。",
  });

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
            message: responseBody.message || `承認状態一覧の取得に失敗しました。HTTP ${response.status}`,
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
          message: "APIに接続できませんでした。",
        });
      }
    }

    void fetchApprovalStatuses();

    return () => {
      abortController.abort();
    };
  }, []);

  useEffect(() => {
    if (selectedTargetId === null) {
      setApprovalDetailState({
        status: "idle",
        item: null,
        message: "対象を選択すると承認状態の詳細を表示します。",
      });
      return;
    }

    const abortController = new AbortController();

    async function fetchApprovalDetail(): Promise<void> {
      setApprovalDetailState({
        status: "loading",
        item: null,
        message: "承認状態詳細を取得しています。",
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
            message: responseBody.message || `承認状態詳細の取得に失敗しました。HTTP ${response.status}`,
          });
          return;
        }

        setApprovalDetailState({
          status: "available",
          item: responseBody.data,
          message: responseBody.message || "承認状態詳細を取得しました。",
        });
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }

        setApprovalDetailState({
          status: "unavailable",
          item: null,
          message: "APIに接続できませんでした。",
        });
      }
    }

    void fetchApprovalDetail();

    return () => {
      abortController.abort();
    };
  }, [selectedTargetId]);

  const selectedItem = approvalDetailState.item;
  const selectedSummary =
    approvalListState.items.find((item) => item.target_id === selectedTargetId) ?? null;

  return (
    <Page title="承認状態確認 / 変更" description="版管理の承認フローに沿って、原本の状態と次に進める操作をAPIから確認します。">
      <section className="approval-flow">
        <FlowStep label="0版 / 過去作成分" />
        <FlowStep label="作成 → Draft" active />
        <FlowStep label="承認申請 → Published" />
        <FlowStep label="承認済み → Archived" />
      </section>
      <section className={`list-status list-status-${approvalListState.status}`} aria-live="polite">
        <div>
          <span>取得状態</span>
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
          <strong>{approvalListState.items.length}</strong>
        </div>
        <div>
          <span>選択中</span>
          <strong>{selectedSummary?.target_key ?? "未選択"}</strong>
        </div>
        <p>{approvalListState.message}</p>
      </section>
      {approvalListState.status === "available" && approvalListState.items.length === 0 ? (
        <section className="empty-state">
          <h2>承認対象はまだありません</h2>
          <p>原本データが追加されると、承認状態の一覧をここで確認できます。</p>
        </section>
      ) : (
        <DataTable
          columns={["対象", "版数", "現在状態", "次の操作", "利用モジュール", "更新日", "操作"]}
          rows={approvalListState.items.map((item) => [
            `${item.target_key} ${item.target_name}`,
            `v${item.version_no}`,
            <ModuleStatusPill status={item.status} label={item.status_label} />,
            item.next_action,
            `${item.enabled_module_count}/${item.module_count}`,
            item.updated_at,
            <button className="text-button" onClick={() => setSelectedTargetId(item.target_id)}>
              詳細
            </button>,
          ])}
        />
      )}
      <section className={`list-status list-status-${approvalDetailState.status === "idle" ? "loading" : approvalDetailState.status}`} aria-live="polite">
        <div>
          <span>詳細状態</span>
          <strong>
            {approvalDetailState.status === "idle"
              ? "未選択"
              : approvalDetailState.status === "loading"
                ? "取得中"
                : approvalDetailState.status === "available"
                  ? "取得成功"
                  : "取得失敗"}
          </strong>
        </div>
        <div>
          <span>対象ID</span>
          <strong>{selectedTargetId ?? "未選択"}</strong>
        </div>
        <div>
          <span>次の操作</span>
          <strong>{selectedItem?.next_action ?? "-"}</strong>
        </div>
        <p>{approvalDetailState.message}</p>
      </section>
      {selectedItem ? (
        <>
          <section className="detail-layout">
            <div className="facts">
              <Fact label="対象ID" value={selectedItem.target_key} />
              <Fact label="対象名" value={selectedItem.target_name} />
              <Fact label="版" value={`v${selectedItem.version_no}`} />
              <Fact label="状態" value={selectedItem.status_label} />
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
          <section className="section-band approval-detail-grid">
            <div>
              <h2>遷移候補</h2>
              {selectedItem.allowed_transitions.length > 0 ? (
                <div className="approval-transition-list">
                  {selectedItem.allowed_transitions.map((transition) => (
                    <article key={transition.to_status} className="approval-transition-card">
                      <strong>{transition.action_label}</strong>
                      <span>{transition.to_status_label}</span>
                    </article>
                  ))}
                </div>
              ) : (
                <p>この状態から進める承認遷移はありません。</p>
              )}
            </div>
            <div>
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
            </div>
          </section>
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
        <h2>版数ルール</h2>
        <p>Draft 中の修正は Y+1、承認済みは X+1 かつ Y 切り捨てとして扱います。</p>
      </section>
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

function DataTable({ columns, rows }: { columns: string[]; rows: ReactNode[][] }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
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
    "/modules/search": "モジュール → 検索",
    "/modules/list": "検索 → 一覧/詳細",
    "/modules/register": "モジュール → 登録",
    "/documents/search": "原本 → 検索",
    "/documents/create": "原本 → 作成/更新",
    "/approval": "承認状態確認",
  };
  if (path.startsWith("/modules/") && path !== "/modules/search" && path !== "/modules/list") {
    return "モジュール → 詳細";
  }
  return map[path] ?? "一覧/詳細画面";
}

export default App;
