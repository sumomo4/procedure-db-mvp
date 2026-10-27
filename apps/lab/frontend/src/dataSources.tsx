import { useEffect, useRef, useState, type FormEvent } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "./auth";

export type DataSource = {
  source_id: string; name: string; enabled: boolean; description: string;
  file_count: number; export_directory: string; files_updated_at: string | null; generation_ready: boolean;
  generation_mode?: "unit_config" | "uni"; generation_message?: string;
};
type BuildUrl = (path: string) => string;

export function scopedSourceUrl(url: string, sourceId: string) {
  const target = new URL(url, window.location.origin);
  target.searchParams.set("data_source_id", sourceId);
  return target.toString();
}

export function useDataSources(buildUrl: BuildUrl, includeDisabled = false) {
  const [items, setItems] = useState<DataSource[]>([]);
  const [status, setStatus] = useState<"loading" | "available" | "error">("loading");
  const [sourceId, setSourceId] = useState("ssc");
  const [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setStatus("loading"); setItems([]);
    void (async () => {
      try {
        const response = await fetch(buildUrl("/api/v1/case-docs/data-sources" + (includeDisabled ? "?include_disabled=true" : "")), { credentials: "include", signal: controller.signal });
        const body = await response.json();
        if (!response.ok || body.result !== "success" || !body.data) throw new Error();
        if (!controller.signal.aborted) { setItems(body.data.items); setStatus("available"); }
      } catch { if (!controller.signal.aborted) { setItems([]); setStatus("error"); } }
    })();
    return () => controller.abort();
  }, [buildUrl, includeDisabled, reload]);
  const source = items.find(item => item.source_id === sourceId && item.enabled) ?? null;
  return { items, status, sourceId, setSourceId, source, ready: status === "available" && source !== null, refresh: () => setReload(value => value + 1) };
}

export function DataSourceSelector({ catalog, disabled = false }: { catalog: Omit<ReturnType<typeof useDataSources>, "setSourceId"> & { setSourceId: (value: string) => void }; disabled?: boolean }) {
  return <section className="section-band data-source-selector">
    <label>参照元DB<select aria-label="参照元DB" value={catalog.sourceId} disabled={disabled || catalog.status !== "available"} onChange={event => catalog.setSourceId(event.target.value)}>
      {catalog.status === "loading" ? <option value="ssc">取得中</option> : null}
      {catalog.items.filter(item => item.enabled).map(item => <option key={item.source_id} value={item.source_id}>{item.name}</option>)}
    </select></label>
    {catalog.source ? <span>{catalog.source.file_count}ファイル{catalog.source.file_count === 0 ? " / 抽出ファイル未配置" : ""}</span> : null}
    {catalog.status === "error" ? <div role="alert" className="form-feedback form-feedback-error">参照元DBを取得できませんでした。<button type="button" className="secondary" onClick={catalog.refresh}>再読み込み</button></div> : null}
  </section>;
}

export function DataSourcesPage({ buildUrl }: { buildUrl: BuildUrl }) {
  const { user } = useAuth();
  const catalog = useDataSources(buildUrl, user?.role === "admin");
  const [editing, setEditing] = useState<DataSource | "new" | null>(null);
  const [form, setForm] = useState({ source_id: "", name: "", description: "", enabled: true });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (editing) dialog.current?.showModal(); else dialog.current?.close(); }, [editing]);
  if (user?.role !== "admin") return <section className="section-band"><h1>参照元DB管理</h1><p role="alert">この画面を利用する権限がありません。</p></section>;
  function open(item: DataSource | "new") {
    setEditing(item); setError("");
    setForm(item === "new" ? { source_id: "", name: "", description: "", enabled: true } : { source_id: item.source_id, name: item.name, description: item.description, enabled: item.enabled });
  }
  async function save(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(buildUrl("/api/v1/case-docs/data-sources" + (editing === "new" ? "" : "/" + encodeURIComponent(form.source_id))), {
        method: editing === "new" ? "POST" : "PUT", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form),
      });
      const body = await response.json();
      if (!response.ok || body.result !== "success") throw new Error(body.message || "参照元DBを保存できませんでした。");
      setEditing(null); setNotice("参照元DBを保存しました。"); catalog.refresh();
    } catch (exception) { setError(exception instanceof Error ? exception.message : "参照元DBを保存できませんでした。"); }
    finally { setBusy(false); }
  }
  return <>
    <header className="page-header"><h1>参照元DB管理</h1></header>
    <section className="section-band">
      <div className="data-source-heading"><h2>参照元DB一覧</h2><button type="button" className="primary" onClick={() => open("new")}><span aria-hidden="true">+</span>参照元DBを登録</button></div>
      {notice ? <p role="status">{notice}</p> : null}
      {catalog.status === "loading" ? <p role="status">取得中</p> : catalog.status === "error" ? <div role="alert">参照元DBを取得できませんでした。<button className="secondary" type="button" onClick={catalog.refresh}>再読み込み</button></div> :
      <div className="data-source-table"><table><thead><tr><th>参照元DB</th><th>状態</th><th>抽出ファイル</th><th>最終更新</th><th>配置先</th><th>操作</th></tr></thead><tbody>
        {catalog.items.map(item => <tr key={item.source_id}><td><strong>{item.name}</strong><small>{item.source_id}</small><small>{item.description}</small></td>
          <td>{item.enabled ? "有効" : "無効"}</td><td>{item.file_count}件{item.file_count === 0 ? <small>未配置</small> : null}</td>
          <td>{item.files_updated_at ? new Date(item.files_updated_at).toLocaleString("ja-JP") : "-"}</td><td><code>{item.export_directory}</code></td>
          <td><button type="button" className="icon-button" title={`${item.name}を編集`} aria-label={`${item.name}を編集`} onClick={() => open(item)}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m15 4 5 5-11 11-6 1 1-6Z"/><path d="m13 6 5 5"/></svg></button></td></tr>)}
      </tbody></table></div>}
      <NavLink to="/case-docs/placeholders">プレースホルダ設定へ</NavLink>
    </section>
    <dialog ref={dialog} className="data-source-dialog" onCancel={event => { if (busy) event.preventDefault(); else setEditing(null); }}>
      <form onSubmit={event => void save(event)}>
        <h2>{editing === "new" ? "参照元DBを登録" : "参照元DBを編集"}</h2>
        <label>識別子<input aria-label="識別子" value={form.source_id} required pattern="[a-z][a-z0-9_-]*" maxLength={40} readOnly={editing !== "new"} disabled={busy} onChange={event => setForm({ ...form, source_id: event.target.value })}/></label>
        <label>参照元DB名<input aria-label="参照元DB名" value={form.name} required maxLength={80} disabled={busy} onChange={event => setForm({ ...form, name: event.target.value })}/></label>
        <label>説明<textarea value={form.description} maxLength={500} disabled={busy} onChange={event => setForm({ ...form, description: event.target.value })}/></label>
        <label className="data-source-enabled"><input type="checkbox" checked={form.enabled} disabled={busy || form.source_id === "ssc"} onChange={event => setForm({ ...form, enabled: event.target.checked })}/>有効</label>
        {error ? <p role="alert" className="form-feedback form-feedback-error">{error}</p> : null}
        <div className="data-source-actions"><button type="button" className="secondary" disabled={busy} onClick={() => setEditing(null)}>キャンセル</button><button type="submit" className="primary" disabled={busy}>{busy ? "保存中" : "保存"}</button></div>
      </form>
    </dialog>
  </>;
}
