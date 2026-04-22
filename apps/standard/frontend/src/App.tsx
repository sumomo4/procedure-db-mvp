import { NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";

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

  return (
    <section className="excel-preview" aria-label="Excel風モジュールプレビュー">
      <div className="excel-title-grid">
        <div className="excel-cell excel-title-cell">{item.module_name.replace("_CS ", " ")}</div>
        <div className="excel-cell excel-small-heading">時刻</div>
        <div className="excel-cell excel-small-heading">target</div>
        <div className="excel-cell excel-small-heading">P</div>
        <div className="excel-cell excel-device-cell">対象装置</div>
        <div className="excel-cell excel-sequence-cell">通番</div>
        <div className="excel-cell excel-target-value">1</div>
        <div className="excel-cell excel-device-value">{"{{DEVICE_NAME}}"}</div>
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
                <td className="excel-center">{row.time_text ?? ""}</td>
                <td>{row.window_text ?? ""}</td>
                <td>{row.p_text ?? ""}</td>
                <td className="excel-command-cell">{row.command_text ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="excel-remarks">
        <strong>連絡事項</strong>
        <p>Excelの結合セル欄に相当する領域です。Sprint 2では閲覧用の仮表示として扱います。</p>
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
  const [moduleNameInput, setModuleNameInput] = useState("Initial check procedure");
  const [descriptionInput, setDescriptionInput] = useState("Created from module register screen.");
  const [sourcePathInput, setSourcePathInput] = useState("imports/manual-module.xlsx");
  const [createdByInput, setCreatedByInput] = useState("webui");
  const [workTextInput, setWorkTextInput] = useState("Check before work.");
  const [expectedResultInput, setExpectedResultInput] = useState("Ready.");
  const [timeTextInput, setTimeTextInput] = useState("5 min");
  const [windowTextInput, setWindowTextInput] = useState("console");
  const [promptTextInput, setPromptTextInput] = useState(">");
  const [commandTextInput, setCommandTextInput] = useState("show version");
  const [createState, setCreateState] = useState<ModuleCreateState>({
    status: "idle",
    item: null,
    message: "Fill in the minimum fields and save the first module version.",
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();

    setCreateState({
      status: "submitting",
      item: null,
      message: "Creating module and first version...",
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
          rows: [
            {
              row_order: 1,
              row_type: "step",
              major_no: "1",
              middle_no: "1",
              minor_no: "1",
              work_text: workTextInput.trim() || moduleNameInput.trim(),
              indent_level: 0,
              expected_result: expectedResultInput.trim() || undefined,
              time_text: timeTextInput.trim() || undefined,
              window_text: windowTextInput.trim() || undefined,
              p_text: promptTextInput.trim() || undefined,
              command_text: commandTextInput.trim() || undefined,
            },
          ],
        }),
      });

      const responseBody = (await response.json()) as ApiResponse<ModuleDetailData>;

      if (!response.ok || responseBody.result !== "success" || responseBody.data === null) {
        setCreateState({
          status: "error",
          item: null,
          message: responseBody.message || `Module create failed. HTTP ${response.status}`,
        });
        return;
      }

      setCreateState({
        status: "success",
        item: responseBody.data,
        message: responseBody.message || "Module was created.",
      });
      setModuleKeyInput(responseBody.data.module_key);
    } catch (error) {
      setCreateState({
        status: "error",
        item: null,
        message: error instanceof Error ? error.message : "Module create failed.",
      });
    }
  }

  const createdItem = createState.item;

  return (
    <Page title="モジュール登録" description="最小項目でモジュールを登録し、POST /api/v1/modules の保存結果を確認します。">
      <section className="upload-zone" aria-label="モジュール登録の進め方">
        <span className="upload-icon">⇧</span>
        <h2>JSON ベースの最小登録</h2>
        <p>Excel 直接取込は後段に回し、Sprint 3 では WebUI からモジュール本体と最初の 1 行を保存できる状態を先に作ります。</p>
      </section>

      <form className="register-form" onSubmit={handleSubmit}>
        <FormGrid>
          <label>
            モジュールキー
            <input value={moduleKeyInput} onChange={(event) => setModuleKeyInput(event.target.value)} placeholder="MOD-004 または空欄で自動採番" />
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
            取込元パス
            <input value={sourcePathInput} onChange={(event) => setSourcePathInput(event.target.value)} placeholder="imports/manual-module.xlsx" />
          </label>
          <label className="wide">
            説明
            <textarea value={descriptionInput} onChange={(event) => setDescriptionInput(event.target.value)} />
          </label>
        </FormGrid>

        <section className="register-step-card">
          <h2>初回保存する手順行</h2>
          <div className="register-step-grid">
            <label className="wide">
              作業内容
              <textarea value={workTextInput} onChange={(event) => setWorkTextInput(event.target.value)} required />
            </label>
            <label>
              期待結果
              <input value={expectedResultInput} onChange={(event) => setExpectedResultInput(event.target.value)} />
            </label>
            <label>
              時刻
              <input value={timeTextInput} onChange={(event) => setTimeTextInput(event.target.value)} />
            </label>
            <label>
              Window
              <input value={windowTextInput} onChange={(event) => setWindowTextInput(event.target.value)} />
            </label>
            <label>
              Prompt
              <input value={promptTextInput} onChange={(event) => setPromptTextInput(event.target.value)} />
            </label>
            <label className="wide">
              Command
              <input value={commandTextInput} onChange={(event) => setCommandTextInput(event.target.value)} />
            </label>
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
              ? "保存成功"
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
              <span>version {createdItem.version_no}</span>
              <span>{createdItem.status_label}</span>
            </div>
          ) : null}
        </section>

        <Toolbar>
          {createdItem ? (
            <button className="secondary" type="button" onClick={() => navigate(`/modules/${createdItem.module_id}`)}>
              <span aria-hidden="true">↗</span>詳細を開く
            </button>
          ) : null}
          <button className="primary" type="submit" disabled={createState.status === "submitting"}>
            <span aria-hidden="true">✓</span>{createState.status === "submitting" ? "登録中..." : "登録実行"}
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

function DocumentEditPage() {
  const navigate = useNavigate();
  return (
    <Page title="原本作成 / 更新" description="モジュールを組み合わせ、原本を作成または更新します。">
      <FormGrid>
        <label>原本名<input defaultValue="M1確認用 原本A" /></label>
        <label>版数<input defaultValue="0.4" /></label>
        <label>利用モジュール<select defaultValue="MOD-001"><option value="MOD-001">MOD-001 初期点検手順</option><option value="MOD-002">MOD-002 部品交換手順</option></select></label>
        <label>状態<select defaultValue="Draft"><option>Draft</option><option>approval</option><option>archive</option></select></label>
        <label className="wide">作成メモ<textarea defaultValue="モジュール組み合わせ結果を確認し、保存後に詳細へ遷移する。" /></label>
      </FormGrid>
      <section className="section-band">
        <h2>モジュール組み合わせ</h2>
        <DataTable
          columns={["順序", "モジュール", "用途", "状態"]}
          rows={[
            ["1", "初期点検手順", "開始前確認", <StatusPill status="Draft" />],
            ["2", "復旧確認手順", "作業後確認", <StatusPill status="archive" />],
          ]}
        />
      </section>
      <Toolbar>
        <button className="secondary" onClick={() => navigate("/modules/list")}><span aria-hidden="true">←</span>一覧へ戻る</button>
        <button className="primary" onClick={() => navigate("/documents/1")}><span aria-hidden="true">✓</span>保存して詳細へ</button>
      </Toolbar>
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
        <button className="primary" onClick={() => navigate("/documents/create")}><span aria-hidden="true">✎</span>更新する</button>
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
    <div className={`excel-indent indent-level-${indentLevel}`}>
      <span className="excel-indent-slot" aria-hidden="true" />
      <span className="excel-indent-slot" aria-hidden="true" />
      <span className="excel-indent-slot" aria-hidden="true" />
      <span className="excel-indent-slot" aria-hidden="true" />
      <span>{text ?? ""}</span>
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
