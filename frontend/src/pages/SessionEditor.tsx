import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowLeft, ChevronRight, FileText, Layers, Play, Plus, Scissors, Settings } from "react-feather";
import { api, isActive, type Cleanup, type Named, type Session, type Task } from "../api";
import { Player } from "../player";
import { go, useAction, useApp } from "../state";
import { cx, NameInput, Progress, Section, Spinner } from "../ui";
import { isStale, LineRow } from "./LineRow";
import { cleanupMessage } from "./Sessions";
import { SessionSettings, toDraft } from "./SessionSettings";

const PAGE = 50;

export function SessionEditor({ id, projects, back }: { id: string; projects: Named[]; back: string }) {
  const run = useAction();
  const { tasks, track, notify } = useApp();
  const [session, setSession] = useState<Session | null>(null);
  const [draft, setDraft] = useState<ReturnType<typeof toDraft> | null>(null);
  const [settings, setSettings] = useState(false);
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
  async function cleanup() {
    const result = await run(() => api.post<Cleanup>(base + "/takes/cleanup"));
    if (!result) return;
    notify(cleanupMessage(result), result.failures.length > 0);
    void load();
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
          <button className="btn btn-ghost" title="清理所有非当前 Take" disabled={!!active.length} onClick={() => void cleanup()}>
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
              />
            ))}
            <AddLine session={session} onAdded={updated} />
          </div>
        ) : (
          <ImportText session={session} onImported={updated} />
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

function ImportText({ session, onImported }: { session: Session; onImported: (s: Session) => void }) {
  const run = useAction();
  const [text, setText] = useState("");
  const count = text.split("\n").filter((l) => /^\s*\[[^\]]+\]\s*\S/.test(l)).length;
  async function submit() {
    const s = await run(() => api.put<Session>(`/sessions/${session.id}/text`, { text }));
    if (s) onImported(s);
  }
  return (
    <Section title="导入文本" extra={<span className="text-xs text-muted">每行 [说话人] 文本，括号开头的行视为注释</span>}>
      <textarea className="input min-h-64 font-mono text-[13px]" placeholder={"[旁白] 故事从这里开始。\n[小明] 你好！\n（这一行是注释）"} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="mt-3 flex items-center justify-end gap-3">
        <span className="mr-auto text-xs text-muted">解析后点击顶部提示，为每位说话人绑定参考音频</span>
        <span className="text-xs text-muted">识别到 {count} 句</span>
        <button className="btn btn-primary" disabled={!count} onClick={() => void submit()}>
          解析并创建句子
        </button>
      </div>
    </Section>
  );
}
