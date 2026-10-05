import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { AlertTriangle, ArrowLeft, BookOpen, CheckSquare, ChevronRight, Download, FileText, Layers, Play, Plus, Scissors, Settings, Trash2 } from "react-feather";
import { api, download, isActive, type Cleanup, type Named, type Session, type Task } from "../api";
import { Player } from "../player";
import { go, useAction, useApp } from "../state";
import { choose, confirm, cx, Empty, NameInput, Progress, Section, Spinner } from "../ui";
import { isStale, LineRow } from "./LineRow";
import { CLEANUP_CHOICES, cleanupMessage } from "./Sessions";
import { ScriptEditor } from "./ScriptEditor";
import { SessionSettings, toDraft } from "./SessionSettings";

const PAGE = 50;

export function SessionEditor({ id, projects, back }: { id: string; projects: Named[]; back: string }) {
  const run = useAction();
  const { tasks, track, notify } = useApp();
  const [session, setSession] = useState<Session | null>(null);
  const [draft, setDraft] = useState<ReturnType<typeof toDraft> | null>(null);
  const [settings, setSettings] = useState(false);
  const [script, setScript] = useState(false);
  // Multi-select mode: null when off.
  const [picked, setPicked] = useState<Set<string> | null>(null);
  const [page, setPage] = useState(0);
  const base = `/sessions/${id}`;

  const load = async () => {
    const s = await run(() => api.get<Session>(base));
    if (s) setSession(s);
    return s;
  };
  useEffect(() => {
    void load().then((s) => {
      if (!s) return;
      setDraft(toDraft(s));
      setSettings(!s.lines.length || !s.bindings.length);
    });
  }, [id]);

  // Reload whenever one of this session's tasks changes state.
  const own = tasks.filter((t) => t.session_ids.includes(id));
  const active = own.filter(isActive);
  const signature = own.map((t) => t.id + t.status).join();
  useEffect(() => {
    if (session) void load();
  }, [signature]);
  const busyLines = useMemo(() => new Set(active.flatMap((t) => t.line_ids || [])), [active]);

  if (!session || !draft) return <div className="grid h-full place-items-center"><Spinner /></div>;

  const project = projects.find((p) => p.id === session.project_id);
  const generated = session.lines.filter((l) => l.current_take_id).length;
  const stale = session.lines.filter((l) => isStale(l, session)).length;
  const missing = [...new Set(session.lines.map((l) => l.speaker))].filter((s) => !session.bindings.some((b) => b.speaker === s && b.audio_id));
  const pages = Math.ceil(session.lines.length / PAGE);
  const shown = session.lines.slice(page * PAGE, page * PAGE + PAGE);

  const submit = async (path: string) => {
    const task = await run(() => api.post<Task>(base + path));
    if (task) track(task);
  };
  const updated = (s: Session) => setSession(s);
  async function move(lineId: string, direction: number) {
    const ids = session!.lines.map((l) => l.id);
    const i = ids.indexOf(lineId);
    [ids[i], ids[i + direction]] = [ids[i + direction], ids[i]];
    const s = await run(() => api.put<Session>(base + "/order", { line_ids: ids }));
    if (s) setSession(s);
  }
  async function cleanup(e: MouseEvent) {
    const mode = await choose(e, "清理此 session 的音频", CLEANUP_CHOICES);
    if (!mode) return;
    const result = await run(() => api.post<Cleanup>(`${base}/takes/cleanup?mode=${mode}`));
    if (!result) return;
    notify(cleanupMessage(result), result.failures.length > 0);
    void load();
  }
  const chosen = picked ? session.lines.filter((l) => picked.has(l.id)).map((l) => l.id) : [];
  const toggle = (lineId: string) =>
    setPicked((p) => {
      const next = new Set(p);
      if (!next.delete(lineId)) next.add(lineId);
      return next;
    });
  async function downloadPicked() {
    await run(() => download(`${base}/lines/download`, { ids: chosen }, `${session!.name}.zip`));
  }
  async function cleanupPicked(e: MouseEvent) {
    if (!(await confirm(e, `清理所选 ${chosen.length} 句中未使用的 Take？每句保留当前 Take。`, "清理"))) return;
    const result = await run(() => api.post<Cleanup>(`${base}/lines/takes/cleanup`, { ids: chosen }));
    if (!result) return;
    notify(cleanupMessage(result), result.failures.length > 0);
    void load();
  }
  async function deletePicked(e: MouseEvent) {
    const takes = session!.lines.filter((l) => picked!.has(l.id)).reduce((n, l) => n + l.takes.length, 0);
    if (!(await confirm(e, `删除所选 ${chosen.length} 句及其 ${takes} 个 Take？`))) return;
    const s = await run(() => api.post<Session>(`${base}/lines/delete`, { ids: chosen }));
    if (!s) return;
    setSession(s);
    setPicked(new Set());
  }
  async function rename(name: string) {
    // Save the stored settings with only the name changed; unsaved edits in the draft stay.
    const s = await run(() => api.put<Session>(base, { ...toDraft(session!), name }));
    if (!s) return false;
    setSession(s);
    setDraft({ ...draft!, name: s.name });
    return true;
  }
  function bindMissing() {
    const have = new Set(draft!.bindings.map((b) => b.speaker));
    const added = missing.filter((s) => !have.has(s)).map((speaker) => ({ speaker, role_id: null, audio_id: null }));
    setDraft({ ...draft!, bindings: [...draft!.bindings, ...added] });
    setSettings(true);
  }

  return (
    <div className="min-h-full">
      <div className="sticky top-0 z-20 border-b border-line bg-bg/90 backdrop-blur">
        <div className="flex min-h-12 items-center gap-2 px-4 py-1.5 lg:px-6">
          <button className="btn btn-ghost btn-icon" onClick={() => go(back)} aria-label="返回">
            <ArrowLeft size={16} />
          </button>
          <nav className="flex min-w-0 flex-1 flex-wrap items-center gap-x-1 text-[13px] leading-snug">
            <button className="max-w-[24rem] cursor-pointer text-left text-muted [overflow-wrap:anywhere] hover:text-fg" onClick={() => go(`projects/${session.project_id}`)}>
              {project?.name || "项目"}
            </button>
            <ChevronRight size={13} className="shrink-0 text-muted" />
            <NameInput className="max-w-[32rem] py-0.5" label="Session 名称" value={session.name} onSave={rename} />
          </nav>
          <button className={cx("btn btn-ghost", settings && "bg-hover text-fg")} onClick={() => setSettings(!settings)}>
            <Settings size={14} />
            <span className="hidden md:inline">设置</span>
          </button>
          <button className="btn btn-ghost" title="编辑台本：批量增删改句子" onClick={() => setScript(true)}>
            <BookOpen size={14} />
            <span className="hidden md:inline">台本</span>
          </button>
          <button className="btn btn-ghost" title="清理 Take" disabled={!!active.length} onClick={(e) => void cleanup(e)}>
            <Scissors size={14} />
            <span className="hidden md:inline">清理</span>
          </button>
          <button className="btn" disabled={!generated || !!active.length} onClick={() => void submit("/merge")}>
            <Layers size={14} />
            合并
          </button>
          <button className="btn btn-primary" disabled={!session.lines.length || missing.length > 0} onClick={() => void submit("/generate")}>
            <Play size={13} fill="currentColor" />
            全部生成
          </button>
        </div>
        {active.length > 0 && (
          <div className="flex items-center gap-3 px-4 pb-2 text-xs text-muted lg:px-6">
            <Spinner />
            <span className="truncate">{active[0].message || "排队中"}</span>
            <Progress value={active[0].progress} className="max-w-60 flex-1" />
            {active.length > 1 && <span>另有 {active.length - 1} 个任务</span>}
          </div>
        )}
      </div>

      <div className="mx-auto max-w-[1280px] space-y-4 px-4 py-5 lg:px-6">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="chip">{session.lines.length} 句</span>
          <span className="chip">
            已生成 {generated}/{session.lines.length}
          </span>
          <span className="chip">{session.lines.reduce((n, l) => n + l.takes.length, 0)} 个 Take</span>
          <span className="chip">{session.bindings.length} 位说话人</span>
          {stale > 0 && <span className="chip bg-warn/15 text-warn">{stale} 句已过期</span>}
          {missing.length > 0 && (
            <button className="chip cursor-pointer bg-warn/15 text-warn hover:underline" onClick={bindMissing}>
              <AlertTriangle size={11} />
              未绑定：{missing.join("、")} · 去绑定
            </button>
          )}
          <span className="flex-1" />
          {picked && (
            <span className="flex items-center gap-0.5">
              <span className="mr-1 text-xs text-muted">已选 {chosen.length}</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setPicked(chosen.length === session.lines.length ? new Set() : new Set(session.lines.map((l) => l.id)))}>
                {chosen.length === session.lines.length ? "全不选" : "全选"}
              </button>
              <button className="tip btn btn-ghost btn-sm btn-icon" data-tip="下载所选的当前 Take（zip）" aria-label="下载所选" disabled={!chosen.length} onClick={() => void downloadPicked()}>
                <Download size={14} />
              </button>
              <button className="tip btn btn-ghost btn-sm btn-icon" data-tip="清理所选句子未使用的 Take" aria-label="清理所选" disabled={!chosen.length || !!active.length} onClick={(e) => void cleanupPicked(e)}>
                <Scissors size={14} />
              </button>
              <button className="tip btn btn-ghost btn-sm btn-icon btn-danger" data-tip="删除所选句子" aria-label="删除所选" disabled={!chosen.length || !!active.length} onClick={(e) => void deletePicked(e)}>
                <Trash2 size={14} />
              </button>
            </span>
          )}
          {session.lines.length > 0 && (
            <button
              className={cx("tip btn btn-ghost btn-sm btn-icon", picked && "bg-hover text-fg")}
              data-tip={picked ? "退出多选" : "多选"}
              aria-label="多选"
              onClick={() => setPicked(picked ? null : new Set())}
            >
              <CheckSquare size={14} />
            </button>
          )}
        </div>

        {settings && (
          <Section title="Session 设置">
            <SessionSettings
              draft={draft}
              setDraft={setDraft}
              session={session}
              projects={projects}
              onSaved={(s) => {
                setSession(s);
                setDraft(toDraft(s));
                if (back.startsWith("projects/") && s.project_id !== session.project_id) go(`projects/${s.project_id}/sessions/${s.id}`);
              }}
            />
          </Section>
        )}

        {session.lines.length ? (
          <div className="card overflow-hidden">
            {shown.map((line, i) => (
              <LineRow
                key={line.id}
                line={line}
                session={session}
                busy={busyLines.has(line.id)}
                first={page === 0 && i === 0}
                last={page * PAGE + i === session.lines.length - 1}
                onChange={updated}
                move={(d) => void move(line.id, d)}
                selecting={!!picked}
                selected={picked?.has(line.id)}
                onSelect={() => toggle(line.id)}
              />
            ))}
            <AddLine session={session} onAdded={updated} />
          </div>
        ) : (
          <Section>
            <Empty icon={<BookOpen size={18} />} title="还没有句子">
              <button className="btn btn-primary mt-3" onClick={() => setScript(true)}>
                编辑台本
              </button>
            </Empty>
          </Section>
        )}

        {pages > 1 && (
          <div className="flex items-center justify-center gap-1">
            {Array.from({ length: pages }, (_, n) => (
              <button key={n} className={cx("btn btn-sm min-w-7", n === page ? "btn-primary" : "btn-ghost")} onClick={() => setPage(n)}>
                {n + 1}
              </button>
            ))}
          </div>
        )}

        {session.outputs.length > 0 && (
          <Section title="合并结果" extra={<span className="text-xs text-muted">{session.outputs.length} 个</span>}>
            <div className="space-y-1.5">
              {[...session.outputs].reverse().map((audioId, i) => (
                <div key={audioId} className="flex items-center gap-2">
                  <span className="w-14 text-xs text-muted">#{session.outputs.length - i}</span>
                  <Player id={audioId} rename className="flex-1" />
                  <button
                    className="btn btn-sm"
                    onClick={async () => {
                      const task = await run(() => api.post<Task>("/subtitles", { audio_id: audioId, model: "base", language: "zh" }));
                      if (task) track(task);
                    }}
                  >
                    <FileText size={12} />
                    生成字幕
                  </button>
                </div>
              ))}
            </div>
          </Section>
        )}
      </div>
      {script && (
        <ScriptEditor
          session={session}
          onClose={() => setScript(false)}
          onApplied={(s) => {
            setSession(s);
            setScript(false);
          }}
        />
      )}
    </div>
  );
}

function AddLine({ session, onAdded }: { session: Session; onAdded: (s: Session) => void }) {
  const run = useAction();
  const speakers = session.bindings.map((b) => b.speaker);
  const [speaker, setSpeaker] = useState(session.lines.at(-1)?.speaker || speakers[0] || "");
  const [text, setText] = useState("");
  async function add() {
    const s = await run(() => api.post<Session>(`/sessions/${session.id}/lines`, { speaker, text }));
    if (!s) return;
    onAdded(s);
    setText("");
  }
  return (
    <div className="grid grid-cols-[44px_112px_minmax(0,1fr)_auto] items-center gap-x-2 border-t border-dashed border-line bg-panel px-3 py-1.5">
      <Plus size={14} className="text-muted" />
      <input className="input h-8 px-1.5" list="speakers" placeholder="说话人" value={speaker} onChange={(e) => setSpeaker(e.target.value)} />
      <datalist id="speakers">
        {speakers.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
      <input className="input" placeholder="添加一句，回车确认" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && speaker.trim() && text.trim() && void add()} />
      <button className="btn btn-sm" disabled={!speaker.trim() || !text.trim()} onClick={() => void add()}>
        添加
      </button>
    </div>
  );
}
