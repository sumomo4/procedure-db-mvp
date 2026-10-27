import { useEffect, useRef, useState, type ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "./auth";
import { DataSourceSelector, scopedSourceUrl, useDataSources } from "./dataSources";

type Option = { value: string; label: string };
export type UniAssignment = { slot_key: string; device_type: string; system: string | null; host_name: string; column_name?: string | null };
export type UniWork = { block: string; building: string; cluster_no: number; prefecture: string; area: string; hostname_prefix: string; pair_building: string };
export type UniTargetWork = UniWork & { target_no: number; slot_keys: string[] };
type Candidates = { work: UniWork; devices: Array<UniAssignment & { available: boolean; message: string }> };
type TargetForm = { key: number; block: string; building: string; cluster: string; device_keys: string[]; candidates: Candidates | null };
type Selection = { block: string; building: string; cluster_no: number; device_keys: string[] };
type Preview = {
  context: { data_source_revision: string; target_contexts: UniTargetWork[]; target_groups: UniAssignment[][] };
  unresolved_count: number;
  cells: Array<{ target_no: number | null; sheet_name: string; cell: string; template_text: string; resolved_text: string; unresolved_placeholders: string[] }>;
};
type PickerProps = { targetNo: number; options: UniAssignment[]; selectedKeys: string[]; disabled: boolean; onChange: (keys: string[]) => void };
type WorkflowProps = {
  catalog: ReturnType<typeof useDataSources>;
  buildUrl: (path: string) => string;
  fetchApi: (url: string, options?: RequestInit) => Promise<Response>;
  renderTable: (columns: string[], rows: ReactNode[][]) => ReactNode;
  renderPicker: (props: PickerProps) => ReactNode;
  saveWorkbook: (payload: Record<string, unknown>, sourceId: string) => Promise<string | null>;
};

function Feedback({ message, error = false }: { message: string; error?: boolean }) {
  return message ? <p className={`form-feedback form-feedback-${error ? "error" : "neutral"}`} role={error ? "alert" : "status"}>{message}</p> : null;
}

function UniTargetEditor({ form, number, blocks, disabled, sourceId, onChange, onRemove, canRemove, ...shared }: {
  form: TargetForm; number: number; blocks: Option[]; disabled: boolean; sourceId: string;
  onChange: (form: TargetForm) => void; onRemove: () => void; canRemove: boolean;
} & Pick<WorkflowProps, "buildUrl" | "fetchApi" | "renderPicker" | "renderTable">) {
  const [buildings, setBuildings] = useState<Option[]>([]);
  const [clusters, setClusters] = useState<Option[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const requestRef = useRef<AbortController | null>(null);
  const workKey = JSON.stringify([sourceId, form.block, form.building, form.cluster]);
  const currentKey = useRef(workKey); currentKey.current = workKey;
  const scoped = (path: string) => scopedSourceUrl(shared.buildUrl(path), sourceId);
  useEffect(() => {
    requestRef.current?.abort(); setLoading(false); setMessage("");
    return () => requestRef.current?.abort();
  }, [workKey]);
  useEffect(() => {
    const controller = new AbortController(); setBuildings([]); setOptionsLoading(false);
    if (!form.block) return () => controller.abort();
    setOptionsLoading(true);
    void (async () => {
      try {
        const url = new URL(scoped("/api/v1/case-docs/master/buildings")); url.searchParams.set("block", form.block);
        const response = await shared.fetchApi(url.toString(), { signal: controller.signal }); const body = await response.json();
        if (controller.signal.aborted) return;
        if (!response.ok || !body.data) throw new Error(body.message || "ビルを取得できませんでした。");
        setBuildings(body.data.items);
      } catch (error) { if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "ビルを取得できませんでした。"); }
      finally { if (!controller.signal.aborted) setOptionsLoading(false); }
    })();
    return () => controller.abort();
  }, [sourceId, form.block]);
  useEffect(() => {
    const controller = new AbortController(); setClusters([]);
    if (!form.block || !form.building) return () => controller.abort();
    void (async () => {
      try {
        const url = new URL(scoped("/api/v1/case-docs/uni/clusters"));
        url.searchParams.set("block", form.block); url.searchParams.set("building", form.building);
        const response = await shared.fetchApi(url.toString(), { signal: controller.signal }); const body = await response.json();
        if (controller.signal.aborted) return;
        if (!response.ok || !body.data) throw new Error(body.message || "クラスタ番号を取得できませんでした。");
        setClusters(body.data.items);
        if (!body.data.items.length) setMessage("このブロックには有効なクラスタ番号がありません。");
      } catch (error) { if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "クラスタ番号を取得できませんでした。"); }
    })();
    return () => controller.abort();
  }, [sourceId, form.block, form.building]);
  function change(patch: Partial<TargetForm>) { onChange({ ...form, ...patch, device_keys: [], candidates: null }); }
  async function loadCandidates() {
    if (disabled || loading || !form.block || !form.building || !form.cluster) return;
    const controller = new AbortController(); requestRef.current?.abort(); requestRef.current = controller;
    const key = workKey; setLoading(true); setMessage("");
    onChange({ ...form, candidates: null, device_keys: [] });
    try {
      const response = await shared.fetchApi(scoped("/api/v1/case-docs/uni/target-candidates"), {
        method: "POST", headers: { "Content-Type": "application/json" }, signal: controller.signal,
        body: JSON.stringify({ block: form.block, building: form.building, cluster_no: Number(form.cluster) }),
      });
      const body = await response.json();
      if (controller.signal.aborted || key !== currentKey.current) return;
      if (!response.ok || body.result !== "success" || !body.data) throw new Error(body.message || "対象装置を確認できませんでした。");
      onChange({ ...form, candidates: body.data, device_keys: [] });
    } catch (error) { if (!controller.signal.aborted && key === currentKey.current) setMessage(error instanceof Error ? error.message : "対象装置を確認できませんでした。"); }
    finally { if (!controller.signal.aborted && key === currentKey.current) setLoading(false); }
  }
  const unmatched = form.candidates?.devices.filter(item => !item.available) ?? [];
  return <section className="uni-target-editor" aria-label={`target ${number}の対象工事`}>
    <header><h3>target {number}</h3><button className="icon-button secondary" type="button" aria-label={`target ${number}を削除`} title={`target ${number}を削除`} disabled={disabled || !canRemove} onClick={onRemove}>×</button></header>
    <div className="uni-target-fields">
      <label>ブロック<select aria-label={`target ${number}のブロック`} value={form.block} disabled={disabled || !blocks.length} onChange={event => change({ block: event.target.value, building: "", cluster: "" })}><option value="">選択してください</option>{blocks.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      <label>ビル<select aria-label={`target ${number}のビル`} value={form.building} disabled={disabled || optionsLoading || !buildings.length} onChange={event => change({ building: event.target.value, cluster: "" })}><option value="">選択してください</option>{buildings.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      <label>クラスタ番号<select aria-label={`target ${number}のクラスタ番号`} value={form.cluster} disabled={disabled || !clusters.length} onChange={event => change({ cluster: event.target.value })}><option value="">選択してください</option>{clusters.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
    </div>
    <div className="uni-target-candidate-action"><button className="secondary" type="button" disabled={disabled || loading || !form.cluster} onClick={() => void loadCandidates()}><span aria-hidden="true">✓</span>{loading ? "照合中" : "対象装置を確認"}</button><Feedback message={message} error /></div>
    {form.candidates ? <>
      <dl className="uni-target-facts"><div><dt>府県</dt><dd>{form.candidates.work.prefecture}</dd></div><div><dt>収容エリア</dt><dd>{form.candidates.work.area}</dd></div><div><dt>ホスト名接頭辞</dt><dd><code>{form.candidates.work.hostname_prefix}</code></dd></div><div><dt>ペアビル</dt><dd>{form.candidates.work.pair_building || "-"}</dd></div></dl>
      {shared.renderPicker({ targetNo: number, options: form.candidates.devices.filter(item => item.available), selectedKeys: form.device_keys, disabled, onChange: device_keys => onChange({ ...form, device_keys }) })}
      {!form.candidates.devices.some(item => item.available) ? <Feedback error message="照合できる対象装置がありません。参照データを確認してください。" /> : null}
      {unmatched.length ? <details className="uni-unmatched"><summary>照合できない装置 {unmatched.length}件</summary>{shared.renderTable(["装置", "生成したホスト名", "確認結果"], unmatched.map(item => [item.column_name ?? item.slot_key, item.host_name, item.message]))}</details> : null}
    </> : null}
  </section>;
}

export function UniCaseDocsPage(props: WorkflowProps) {
  const { catalog, buildUrl, fetchApi, renderTable, renderPicker } = props;
  const navigate = useNavigate(); const { user } = useAuth(); const [params] = useSearchParams();
  const [sources, setSources] = useState<Array<{ source_doc_id: number; source_doc_key: string; source_doc_name: string }>>([]);
  const [sourceId, setSourceId] = useState(""); const [blocks, setBlocks] = useState<Option[]>([]);
  const [step, setStep] = useState<1 | 2 | 3>(1); const [message, setMessage] = useState(""); const [busy, setBusy] = useState(false);
  const [caseName, setCaseName] = useState(""); const [preview, setPreview] = useState<Preview | null>(null);
  const [acknowledged, setAcknowledged] = useState(false); const [onlyUnresolved, setOnlyUnresolved] = useState(true);
  const nextKey = useRef(1);
  const blank = (): TargetForm => ({ key: nextKey.current++, block: "", building: "", cluster: "", device_keys: [], candidates: null });
  const [targets, setTargets] = useState<TargetForm[]>(() => [blank()]);
  const currentKey = useRef(""); const apiSourceId = catalog.sourceId;
  const scoped = (path: string) => scopedSourceUrl(buildUrl(path), apiSourceId);
  const selections: Selection[] = targets.map(item => ({ block: item.block, building: item.building, cluster_no: Number(item.cluster), device_keys: item.device_keys }));
  const reviewKey = JSON.stringify([apiSourceId, sourceId, selections]); currentKey.current = reviewKey;
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, [step]);
  useEffect(() => { setPreview(null); setAcknowledged(false); setStep(current => current === 3 ? 2 : current); }, [reviewKey]);
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const response = await fetchApi(buildUrl("/api/v1/source-docs?status=published"), { signal: controller.signal }); const body = await response.json();
        if (controller.signal.aborted) return;
        if (!response.ok || !body.data) throw new Error(body.message || "原本一覧を取得できませんでした。");
        setSources(body.data.items);
        const requested = params.get("source_doc_id");
        setSourceId(String(body.data.items.find((item: { source_doc_id: number }) => String(item.source_doc_id) === requested)?.source_doc_id ?? body.data.items[0]?.source_doc_id ?? ""));
      } catch (error) { if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "原本一覧を取得できませんでした。"); }
    })();
    return () => controller.abort();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    if (!catalog.source?.generation_ready) return () => controller.abort();
    void (async () => {
      try {
        const response = await fetchApi(scoped("/api/v1/case-docs/master/blocks"), { signal: controller.signal }); const body = await response.json();
        if (controller.signal.aborted) return;
        if (!response.ok || !body.data) throw new Error(body.message || "UNIのブロックを取得できませんでした。");
        setBlocks(body.data.items);
      } catch (error) { if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : "UNIのブロックを取得できませんでした。"); }
    })();
    return () => controller.abort();
  }, [apiSourceId, catalog.source?.generation_ready]);
  useEffect(() => {
    if (!sourceId) return;
    const controller = new AbortController();
    setTargets([blank()]); setStep(1);
    void (async () => {
      try {
        const response = await fetchApi(buildUrl(`/api/v1/source-docs/${sourceId}`), { signal: controller.signal }); const body = await response.json();
        if (controller.signal.aborted || !response.ok || !body.data) return;
        const count = Math.min(20, (body.data.items ?? []).filter((item: { enabled: boolean }) => item.enabled).reduce((maximum: number, item: { rows: Array<{ device_entries: Array<{ slot_no: number }> }> }) => item.rows.reduce((n, row) => row.device_entries.reduce((m, entry) => Math.max(m, entry.slot_no), n), maximum), 1));
        setTargets(current => current.length < count ? [...current, ...Array.from({ length: count - current.length }, blank)] : current);
      } catch { /* Targets remain manually addable when source detail is unavailable. */ }
    })();
    return () => controller.abort();
  }, [sourceId]);
  const allValid = targets.length > 0 && targets.every(item => item.candidates && item.device_keys.length > 0);
  const readyToSave = preview !== null && (preview.unresolved_count === 0 || acknowledged);
  const payload = (includeRevision = true): Record<string, unknown> => ({ data_source_id: apiSourceId, source_doc_id: Number(sourceId), uni_targets: selections,
    ...(includeRevision && preview ? { expected_data_source_revision: preview.context.data_source_revision } : {}) });
  async function review() {
    if (busy || !allValid || !sourceId) return;
    const key = reviewKey; setBusy(true); setMessage(""); setPreview(null);
    try {
      const response = await fetchApi(buildUrl("/api/v1/case-docs/preview"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload(false)) });
      const body = await response.json();
      if (currentKey.current !== key) return;
      if (!response.ok || !body.data) throw new Error(body.message || "置換結果を確認できませんでした。");
      setPreview(body.data); setAcknowledged(false); setOnlyUnresolved(true); setStep(3);
    } catch (error) { if (currentKey.current === key) setMessage(error instanceof Error ? error.message : "置換結果を確認できませんでした。"); }
    finally { setBusy(false); }
  }
  async function output(excel: boolean) {
    if (busy || !readyToSave || (!excel && !caseName.trim())) return;
    setBusy(true); setMessage("");
    try {
      if (excel) {
        const filename = await props.saveWorkbook(payload(), sourceId);
        setMessage(filename ? `案件CS Excelを出力しました。${filename}` : "保存先の選択をキャンセルしました。");
      } else {
        const response = await fetchApi(buildUrl("/api/v1/case-docs/instances"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...payload(), case_name: caseName.trim(), created_by: user?.displayName ?? "" }) });
        const body = await response.json();
        if (!response.ok || !body.data) throw new Error(body.message || "案件CSを保存できませんでした。");
        navigate(`/case-docs/executions/${body.data.case_document_id}`);
      }
    } catch (error) { setMessage(error instanceof Error ? error.message : "処理を完了できませんでした。"); }
    finally { setBusy(false); }
  }
  return <>
    <DataSourceSelector catalog={catalog} disabled={busy} />
    {!catalog.source?.generation_ready ? <Feedback error message={catalog.source?.generation_message || "UNIの案件化に必要な設定・抽出ファイルが不足しています。"} /> : null}
    <nav className="case-doc-steps" aria-label="UNI案件化の手順"><ol>{(["原本", "対象工事・装置", "確認・保存"] as const).map((label, index) => <li key={label}><button type="button" disabled={busy || (index === 1 && (!sourceId || !blocks.length || !catalog.source?.generation_ready)) || (index === 2 && !preview)} aria-current={step === index + 1 ? "step" : undefined} onClick={() => setStep((index + 1) as 1 | 2 | 3)}><span className="case-doc-step-number">{index + 1}</span><strong>{label}</strong><small>{step === index + 1 ? "入力中" : ""}</small></button></li>)}</ol></nav>
    {step === 1 ? <section className="case-doc-panel"><h2 ref={heading} tabIndex={-1}>原本</h2><label className="uni-source-choice">原本<select aria-label="原本" value={sourceId} disabled={busy || !sources.length} onChange={event => setSourceId(event.target.value)}>{sources.map(item => <option key={item.source_doc_id} value={item.source_doc_id}>{item.source_doc_key} / {item.source_doc_name}</option>)}</select></label><div className="case-doc-stage-actions"><span /><button className="primary" type="button" disabled={busy || !sourceId || !blocks.length || !catalog.source?.generation_ready} onClick={() => setStep(2)}>対象工事・装置を選ぶ<span aria-hidden="true">→</span></button></div></section> : null}
    {step === 2 ? <section className="section-band uni-target-stage"><h2 ref={heading} tabIndex={-1}>targetごとの対象工事・装置</h2><div className="uni-target-list">{targets.map((target, index) => <UniTargetEditor key={target.key} form={target} number={index + 1} blocks={blocks} disabled={busy} sourceId={apiSourceId} buildUrl={buildUrl} fetchApi={fetchApi} renderTable={renderTable} renderPicker={renderPicker} canRemove={targets.length > 1} onRemove={() => setTargets(current => current.filter(item => item.key !== target.key))} onChange={value => setTargets(current => current.map(item => item.key === value.key ? value : item))} />)}</div><button className="secondary" type="button" disabled={busy || targets.length >= 20} onClick={() => setTargets(current => [...current, blank()])}><span aria-hidden="true">+</span>targetを追加</button><div className="case-doc-stage-actions"><button className="secondary" type="button" disabled={busy} onClick={() => setStep(1)}>原本へ戻る</button><button className="primary" type="button" disabled={busy || !allValid} onClick={() => void review()}>{busy ? "確認中" : "置換結果を確認"}<span aria-hidden="true">→</span></button></div></section> : null}
    {step === 3 && preview ? <>
      <section className="section-band case-doc-review-stage"><h2 ref={heading} tabIndex={-1}>確認・保存</h2><label className="case-doc-case-name">案件名<input aria-label="案件名" value={caseName} maxLength={200} required disabled={busy} onChange={event => setCaseName(event.target.value)} /></label><h3>targetごとの対象工事・装置</h3>
        {renderTable(["target", "ブロック", "ビル", "府県", "クラスタ番号", "収容エリア", "ホスト名"], preview.context.target_contexts.map((item, index) => [`target ${item.target_no}`, item.block, item.building, item.prefecture, String(item.cluster_no), item.area, <span className="case-doc-host-names">{preview.context.target_groups[index].map(host => host.host_name).join("\n")}</span>]))}
        <div className={`case-doc-preview-status${preview.unresolved_count ? " has-unresolved" : ""}`} role="status"><strong>{preview.unresolved_count ? `未置換 ${preview.unresolved_count}件` : "未置換の項目はありません"}</strong>{preview.unresolved_count ? <label><input type="checkbox" checked={acknowledged} disabled={busy} onChange={event => setAcknowledged(event.target.checked)} />未置換の項目を残したまま出力・保存することを確認しました</label> : <span>置換確認対象 {preview.cells.length}セル</span>}</div>
        <div className="case-doc-stage-heading"><h3>置換結果</h3>{preview.unresolved_count ? <label><input type="checkbox" checked={onlyUnresolved} onChange={event => setOnlyUnresolved(event.target.checked)} />未置換のみ</label> : null}</div>
        {preview.cells.length ? renderTable(["対象", "セル", "原本の記載", "出力結果", "状態"], preview.cells.filter(cell => !onlyUnresolved || !preview.unresolved_count || cell.unresolved_placeholders.length).map(cell => [cell.target_no ? `target ${cell.target_no}` : "共通欄", <span title={cell.sheet_name}>{cell.cell}</span>, <code>{cell.template_text}</code>, cell.resolved_text, cell.unresolved_placeholders.length ? "未置換" : "置換済み"])) : <p>原本の本文にプレースホルダはありません。</p>}
      </section><section className="section-band case-doc-save-stage"><div className="case-doc-output-actions"><button className="secondary" type="button" disabled={busy || !readyToSave} onClick={() => void output(true)}><span aria-hidden="true">⇩</span>案件CS Excelを出力</button><button className="primary" type="button" disabled={busy || !readyToSave || !caseName.trim()} onClick={() => void output(false)}><span aria-hidden="true">→</span>案件CSを保存して実行前準備へ</button></div><div className="case-doc-stage-actions"><button className="secondary" type="button" disabled={busy} onClick={() => setStep(2)}>対象工事・装置を修正</button></div></section>
    </> : null}
    <Feedback message={message} error={Boolean(message) && !message.includes("出力しました") && !message.includes("キャンセルしました")} />
  </>;
}
