import { useEffect, useState, type MouseEvent } from "react";
import { AlertCircle, ArrowDown, ArrowUp, Check, ChevronDown, RefreshCw, Scissors, Trash2 } from "react-feather";
import { api, currentTake, type Cleanup, type Generation, type Line, type Session, type Task } from "../api";
import { Player } from "../player";
import { useAction, useApp } from "../state";
import { ago, confirm, cx, Spinner } from "../ui";
import { cleanupMessage } from "./Sessions";

/* Snapshot differs from what would be generated now. */
export function isStale(line: Line, session: Session) {
  const take = currentTake(line);
  if (!take) return false;
  const audio = session.bindings.find((b) => b.speaker === line.speaker)?.audio_id ?? null;
  const s = take.snapshot;
  const params = Object.keys(session.generation) as (keyof Generation)[];
  return s.text !== line.text || s.speaker !== line.speaker || s.audio_id !== audio || params.some((k) => s.generation[k] !== session.generation[k]);
}

interface Props {
  line: Line;
  session: Session;
  busy: boolean;
  first: boolean;
  last: boolean;
  onChange: (s: Session) => void;
  move: (direction: number) => void;
  /* Multi-select mode: a checkbox replaces the move arrows. */
  selecting?: boolean;
  selected?: boolean;
  onSelect?: () => void;
}

export function LineRow({ line, session, busy, first, last, onChange, move, selecting, selected, onSelect }: Props) {
  const run = useAction();
  const { track, notify } = useApp();
  const [text, setText] = useState(line.text);
  const [open, setOpen] = useState(false);
  useEffect(() => setText(line.text), [line.text]);
  const base = `/sessions/${session.id}/lines/${line.id}`;
  const take = currentTake(line);
  const stale = isStale(line, session);
  const speakers = session.bindings.map((b) => b.speaker);
  const unbound = !session.bindings.some((b) => b.speaker === line.speaker && b.audio_id);

  async function save(patch: Partial<Pick<Line, "text" | "speaker">>) {
    const next = { text: line.text, speaker: line.speaker, ...patch };
    if (!next.text.trim()) return setText(line.text);
    const updated = await run(() => api.put<Session>(base, next));
    if (updated) onChange(updated);
  }
  async function generate() {
    if (text !== line.text) await save({ text });
    const task = await run(() => api.post<Task>(base + "/generate"));
    if (task) track(task);
  }
  async function remove(e: MouseEvent) {
    if (!(await confirm(e, `删除 #${line.index} 及其 ${line.takes.length} 个 Take？`))) return;
    const updated = await run(() => api.del<Session>(base));
    if (updated) onChange(updated);
  }
  async function select(takeId: string) {
    const updated = await run(() => api.put<Session>(base + "/current-take", { take_id: takeId }));
    if (updated) onChange(updated);
  }
  async function cleanup() {
    const result = await run(() => api.post<Cleanup>(base + "/takes/cleanup"));
    if (!result) return;
    notify(cleanupMessage(result), result.failures.length > 0);
    const updated = await run(() => api.get<Session>(`/sessions/${session.id}`));
    if (updated) onChange(updated);
  }

  return (
    <div className={cx("group relative border-b border-line last:border-0", busy && "bg-accent-soft/40", selected && "bg-accent-soft/70")}>
      {selecting && (
        // The whole row toggles; its inputs and players stay out of reach while selecting.
        <button
          className="absolute inset-0 z-10 cursor-pointer transition-colors hover:bg-fg/[0.06] focus-visible:bg-fg/[0.06] focus-visible:outline-none"
          aria-pressed={!!selected}
          aria-label={`选择 #${line.index}`}
          onClick={onSelect}
        />
      )}
      <div className="grid grid-cols-[44px_112px_minmax(0,1fr)] items-start gap-x-2 px-3 py-1.5 lg:grid-cols-[44px_112px_minmax(0,1fr)_230px_64px]">
        {selecting ? (
          <span className="flex h-8 items-center gap-2 text-xs text-muted tabular-nums">
            <input type="checkbox" tabIndex={-1} readOnly aria-hidden className="pointer-events-none size-4 accent-[var(--accent)]" checked={!!selected} />
            #{line.index}
          </span>
        ) : (
          <div className="flex h-8 items-center gap-0.5 text-xs text-muted tabular-nums">
            <span className="group-hover:hidden">#{line.index}</span>
            <span className="hidden group-hover:flex">
              <button className="cursor-pointer rounded p-0.5 hover:bg-hover hover:text-fg disabled:opacity-30" disabled={first} onClick={() => move(-1)} aria-label="上移">
                <ArrowUp size={12} />
              </button>
              <button className="cursor-pointer rounded p-0.5 hover:bg-hover hover:text-fg disabled:opacity-30" disabled={last} onClick={() => move(1)} aria-label="下移">
                <ArrowDown size={12} />
              </button>
            </span>
          </div>
        )}
        <select
          className={cx("input h-8 truncate border-transparent bg-transparent px-1.5 font-medium text-accent hover:border-line", unbound && "text-warn")}
          title={unbound ? "该说话人未绑定参考音频" : line.speaker}
          value={line.speaker}
          onChange={(e) => void save({ speaker: e.target.value })}
        >
          {[...new Set([line.speaker, ...speakers])].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <textarea
          rows={1}
          className={cx("input min-h-8 resize-none border-transparent bg-transparent px-2 py-1.5 leading-normal [field-sizing:content] hover:border-line", text !== line.text && "border-accent/50")}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => text !== line.text && void save({ text })}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              e.currentTarget.blur();
            }
            if (e.key === "Escape") setText(line.text);
          }}
        />
        <div className="col-span-3 col-start-3 flex min-w-0 items-center gap-1.5 pb-1 lg:col-span-1 lg:col-start-auto lg:pb-0">
          {busy ? (
            <span className="flex h-8 flex-1 items-center gap-2 text-xs text-accent">
              <Spinner /> 生成中…
            </span>
          ) : (
            <Player id={take?.audio_id} download={false} className="flex-1" />
          )}
          {line.takes.length > 0 && (
            <button
              onClick={() => setOpen(!open)}
              title={stale ? "当前 Take 与文本、参考音频或参数不一致" : "Take 历史"}
              className={cx("chip h-6 cursor-pointer gap-0.5 hover:text-fg", stale && "bg-warn/15 text-warn", open && "chip-accent")}
            >
              {stale && <AlertCircle size={11} />}T{take?.take_index ?? "-"}
              <span className="opacity-60">/{line.takes.length}</span>
              <ChevronDown size={11} className={cx("transition-transform", open && "rotate-180")} />
            </button>
          )}
        </div>
        <div className="col-start-3 flex h-8 items-center justify-end gap-0.5 lg:col-start-auto">
          <button className="btn btn-ghost btn-sm btn-icon" title="生成新 Take" disabled={busy || unbound} onClick={() => void generate()}>
            <RefreshCw size={13} />
          </button>
          <button className="btn btn-ghost btn-sm btn-icon btn-danger opacity-0 group-hover:opacity-100" title="删除句子" onClick={(e) => void remove(e)}>
            <Trash2 size={13} />
          </button>
        </div>
      </div>
      {open && (
        <div className="mx-3 mb-2.5 ml-[56px] rounded-lg bg-panel p-2">
          {[...line.takes].reverse().map((t) => {
            const current = t.id === line.current_take_id;
            return (
              <div key={t.id} className="grid grid-cols-[64px_minmax(0,1fr)_200px_72px] items-center gap-2 rounded-md px-1.5 py-1 hover:bg-hover">
                <span className={cx("text-xs font-medium", current ? "text-accent" : "text-muted")}>Take {t.take_index}</span>
                <span className="truncate text-xs text-muted" title={t.snapshot.text}>
                  {ago(t.created_at)}
                  {t.snapshot.text !== line.text && ` · ${t.snapshot.text}`}
                </span>
                <Player id={t.audio_id} />
                {current ? (
                  <span className="chip chip-accent justify-self-end">
                    <Check size={10} />
                    当前
                  </span>
                ) : (
                  <button className="btn btn-sm justify-self-end" disabled={!t.audio_id} onClick={() => void select(t.id)}>
                    设为当前
                  </button>
                )}
              </div>
            );
          })}
          {line.takes.length > 1 && (
            <button className="btn btn-ghost btn-sm mt-1" onClick={() => void cleanup()}>
              <Scissors size={12} />
              清理其他 Take
            </button>
          )}
        </div>
      )}
    </div>
  );
}
