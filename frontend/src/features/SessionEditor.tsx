import { useEffect, useState } from "react";
import {
  api,
  sessionInput,
  type Audio,
  type Named,
  type Preset,
  type Role,
  type Session,
  type Task,
} from "../api";
import { Advanced, Cleanup, Player } from "../components";
import { Bindings } from "./Bindings";
import { LineEditor } from "./LineEditor";

export function SessionEditor({
  id,
  projects,
  onBack,
  onTask,
  taskVersion,
}: {
  id: string;
  projects: Named[];
  onBack: () => void;
  onTask: (t: Task) => void;
  taskVersion: string;
}) {
  const [session, setSession] = useState<Session | null>(null),
    [draft, setDraft] = useState<Session | null>(null),
    [roles, setRoles] = useState<Role[]>([]),
    [audio, setAudio] = useState<Audio[]>([]),
    [presets, setPresets] = useState<Preset[]>([]),
    [text, setText] = useState(""),
    [error, setError] = useState(""),
    [page, setPage] = useState(0),
    [newLine, setNewLine] = useState(""),
    [newSpeaker, setNewSpeaker] = useState("");
  const base = `/sessions/${id}`;
  async function refresh(reset = false) {
    const s = await api<Session>(base);
    setSession(s);
    if (reset) setDraft(s);
  }
  useEffect(() => {
    let live = true;
    Promise.all([
      api<Session>(base),
      api<Role[]>("/roles"),
      api<Audio[]>("/audio"),
      api<Preset[]>("/presets"),
    ])
      .then(([s, r, a, p]) => {
        if (live) {
          setSession(s);
          setDraft(s);
          setRoles(r);
          setAudio(a);
          setPresets(p);
        }
      })
      .catch((e) => {
        if (live) setError(e.message);
      });
    return () => {
      live = false;
    };
  }, [id]);
  useEffect(() => {
    void refresh().catch((e) => setError(e.message));
  }, [taskVersion]);
  async function action(fn: () => Promise<unknown>) {
    try {
      setError("");
      await fn();
      await refresh();
    } catch (e) {
      setError(String(e));
    }
  }
  if (!session || !draft)
    return <section className="page">{error || "加载 session…"}</section>;
  const project = projects.find((p) => p.id === session.project_id),
    lines = session.lines.slice(page * 20, page * 20 + 20);
  async function move(lineId: string, direction: number) {
    if (!session) return;
    const ids = session.lines.map((l) => l.id),
      i = ids.indexOf(lineId),
      j = i + direction;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    await action(() => api(base + "/order", "PUT", { line_ids: ids }));
  }
  return (
    <section className="session-page">
      <div className="breadcrumb">
        <button onClick={onBack}>← 返回</button>
        <span>
          {project?.name} / <strong>{session.name}</strong>
        </span>
      </div>
      <div className="page">
        <header>
          <p className="eyebrow">有声书 SESSION</p>
          <h1>{session.name}</h1>
          <p className="muted">
            {session.lines.length} 句 ·{" "}
            {session.lines.reduce((n, l) => n + l.takes.length, 0)} 个 Take
          </p>
        </header>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <details className="card" open={session.lines.length === 0}>
          <summary>Session 设置 · 角色与生成参数</summary>
          <div className="stack">
            <div className="grid-fields">
              <label>
                名称
                <input
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                />
              </label>
              <label>
                所属项目
                <select
                  value={draft.project_id}
                  onChange={(e) =>
                    setDraft({ ...draft, project_id: e.target.value })
                  }
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                句间隔（秒）
                <input
                  type="number"
                  min="0"
                  max="30"
                  step="0.1"
                  value={draft.interval}
                  onChange={(e) =>
                    setDraft({ ...draft, interval: Number(e.target.value) })
                  }
                />
              </label>
            </div>
            <Bindings
              value={draft.bindings}
              onChange={(bindings) => setDraft({ ...draft, bindings })}
              roles={roles}
              audio={audio}
            />
            <div className="row">
              <select
                aria-label="多人预设"
                defaultValue=""
                onChange={(e) => {
                  const p = presets.find((p) => p.id === e.target.value);
                  if (p)
                    setDraft({
                      ...draft,
                      bindings: p.bindings,
                      generation: p.generation,
                    });
                }}
              >
                <option value="">读取多人预设</option>
                {presets.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() =>
                  action(async () => {
                    const name = prompt("预设名称", draft.name);
                    if (!name) return;
                    const existing = presets.find((p) => p.name === name);
                    await api(
                      existing ? `/presets/${existing.id}` : "/presets",
                      existing ? "PUT" : "POST",
                      {
                        name,
                        bindings: draft.bindings,
                        generation: draft.generation,
                      },
                    );
                    setPresets(await api("/presets"));
                  })
                }
              >
                保存为预设
              </button>
            </div>
            <Advanced
              value={draft.generation}
              onChange={(generation) => setDraft({ ...draft, generation })}
            />
            <button
              className="primary"
              onClick={() =>
                action(async () => {
                  await api(base, "PUT", sessionInput(draft));
                  await refresh(true);
                })
              }
            >
              保存设置
            </button>
          </div>
        </details>
        {!session.lines.length && (
          <div className="card stack">
            <label>
              有声书文本
              <textarea
                rows={8}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={"[旁白] 故事从这里开始。\n[角色名] 你好。"}
              />
            </label>
            <button
              disabled={!text.trim()}
              onClick={() => action(() => api(base + "/text", "PUT", { text }))}
            >
              解析并保存句子
            </button>
          </div>
        )}
        <div className="toolbar">
          <button
            className="primary"
            disabled={!session.lines.length}
            onClick={() =>
              action(async () =>
                onTask(await api<Task>(base + "/generate", "POST")),
              )
            }
          >
            全部生成新 Take
          </button>
          <button
            disabled={!session.lines.length}
            onClick={() =>
              action(async () =>
                onTask(await api<Task>(base + "/merge", "POST")),
              )
            }
          >
            合并当前 Takes
          </button>
          <Cleanup path={base} onDone={() => void refresh()} />
        </div>
        <div className="stack">
          {lines.map((line) => (
            <LineEditor
              key={line.id}
              line={line}
              referenceId={
                session.bindings.find(
                  (binding) => binding.speaker === line.speaker,
                )?.audio_id || null
              }
              generation={session.generation}
              sessionId={id}
              refresh={() => void refresh().catch((e) => setError(e.message))}
              onTask={onTask}
              move={(direction) => void move(line.id, direction)}
            />
          ))}
        </div>
        <div className="row pagination">
          <button disabled={!page} onClick={() => setPage(page - 1)}>
            上一页
          </button>
          <span>
            {page + 1} / {Math.max(1, Math.ceil(session.lines.length / 20))}
          </span>
          <button
            disabled={(page + 1) * 20 >= session.lines.length}
            onClick={() => setPage(page + 1)}
          >
            下一页
          </button>
        </div>
        <details className="card">
          <summary>添加一句</summary>
          <div className="stack">
            <input
              aria-label="新句角色"
              placeholder="角色名"
              value={newSpeaker}
              onChange={(e) => setNewSpeaker(e.target.value)}
            />
            <textarea
              aria-label="新句文本"
              placeholder="文本"
              value={newLine}
              onChange={(e) => setNewLine(e.target.value)}
            />
            <button
              disabled={!newSpeaker.trim() || !newLine.trim()}
              onClick={() =>
                action(async () => {
                  await api(base + "/lines", "POST", {
                    speaker: newSpeaker,
                    text: newLine,
                  });
                  setNewLine("");
                })
              }
            >
              添加
            </button>
          </div>
        </details>
        {session.outputs.length > 0 && (
          <div className="card stack">
            <h2>合并结果</h2>
            {session.outputs.map((audioId) => (
              <div className="stack" key={audioId}>
                <Player id={audioId} />
                <button
                  onClick={() =>
                    action(async () =>
                      onTask(
                        await api<Task>("/subtitles", "POST", {
                          audio_id: audioId,
                          model: "base",
                          language: "zh",
                        }),
                      ),
                    )
                  }
                >
                  为合并音频生成字幕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
