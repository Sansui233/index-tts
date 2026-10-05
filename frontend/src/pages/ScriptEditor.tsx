import { useMemo, useRef, useState } from "react";
import { AlertCircle, RotateCcw } from "react-feather";
import { api, type Session } from "../api";
import { diffScript, parseScript, scriptBody, toScript, type Row } from "../script";
import { useAction, useStored } from "../state";
import { cx, Modal } from "../ui";

const ROW: Record<Row["kind"], [sign: string, style: string]> = {
  same: [" ", ""],
  modified: ["~", "bg-warn/10"],
  added: ["+", "bg-ok/10"],
  deleted: ["−", "bg-danger/10"],
};

/* Edit the whole session as text; the right pane diffs it against the current lines.
   Unapplied edits are kept per session in this browser until applied or reset. */
export function ScriptEditor({ session, onApplied, onClose }: { session: Session; onApplied: (s: Session) => void; onClose: () => void }) {
  const run = useAction();
  const current = useMemo(() => toScript(session.lines), [session.lines]);
  const [draft, setDraft] = useStored<{ text: string | null }>(`script-draft:${session.id}`, { text: null });
  const text = draft.text ?? current;
  const [changesOnly, setChangesOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const field = useRef<HTMLTextAreaElement>(null);

  const { entries, invalid } = useMemo(() => parseScript(text), [text]);
  const rows = useMemo(() => diffScript(session.lines, entries), [session.lines, entries]);
  const count = (kind: Row["kind"]) => rows.filter((r) => r.kind === kind).length;
  const changed = rows.some((r) => r.kind !== "same");
  const orphaned = rows.reduce((n, r) => n + (r.kind === "deleted" ? r.line.takes.length : 0), 0);

  // Put the caret on a text line and scroll it into view.
  function jump(number: number) {
    const area = field.current;
    if (!area) return;
    const lines = text.split("\n");
    const start = lines.slice(0, number - 1).reduce((n, l) => n + l.length + 1, 0);
    area.focus();
    area.setSelectionRange(start, start + (lines[number - 1]?.length ?? 0));
    const height = area.scrollHeight / Math.max(1, lines.length);
    area.scrollTop = Math.max(0, (number - 4) * height);
  }
  async function apply() {
    setBusy(true);
    const saved = await run(() => api.put<Session>(`/sessions/${session.id}/script`, scriptBody(rows)), "台本已更新");
    setBusy(false);
    if (!saved) return;
    setDraft({ text: null });
    onApplied(saved);
  }

  return (
    <Modal
      wide
      title="台本"
      onClose={onClose}
      footer={
        <>
          <span className="flex items-center gap-2 text-xs">
            <span className="text-ok">+{count("added")}</span>
            <span className="text-warn">~{count("modified")}</span>
            <span className="text-danger">−{count("deleted")}</span>
            {orphaned > 0 && <span className="text-muted">· 删除句子的 {orphaned} 个 Take 文件会保留，可在「清理」中删除</span>}
          </span>
          <span className="flex-1" />
          <button className="btn" onClick={onClose}>
            {draft.text !== null && draft.text !== current ? "稍后继续" : "取消"}
          </button>
          <button className="btn btn-primary" disabled={busy || !changed || invalid.length > 0} onClick={() => void apply()}>
            确认更新
          </button>
        </>
      }
    >
      <div className="grid min-h-0 flex-1 grid-rows-2 md:grid-cols-2 md:grid-rows-1">
        <div className="flex min-h-0 flex-col border-b border-line md:border-r md:border-b-0">
          <div className="flex h-9 shrink-0 items-center gap-2 border-b border-line px-4 text-xs text-muted">
            <span className="flex-1">每行 [说话人] 文本；空行和以括号开头的行为注释</span>
            {draft.text !== null && draft.text !== current && (
              <button className="flex cursor-pointer items-center gap-1 hover:text-fg" onClick={() => setDraft({ text: null })}>
                <RotateCcw size={12} />
                还原
              </button>
            )}
          </div>
          <textarea
            ref={field}
            autoFocus
            spellCheck={false}
            className="min-h-0 flex-1 resize-none bg-transparent px-4 py-3 font-mono text-[13px] leading-6 outline-none"
            placeholder={"[旁白] 故事从这里开始。\n[小明] 你好！\n（这一行是注释）"}
            value={text}
            onChange={(e) => setDraft({ text: e.target.value })}
          />
          {invalid.length > 0 && (
            <div className="max-h-28 shrink-0 overflow-y-auto border-t border-danger/30 bg-danger/5 px-4 py-2 text-xs">
              <p className="mb-1 flex items-center gap-1 font-medium text-danger">
                <AlertCircle size={12} />
                {invalid.length} 行格式无效，修正后才能更新
              </p>
              {invalid.map((l) => (
                <button key={l.number} className="block w-full cursor-pointer truncate text-left text-muted hover:text-fg" onClick={() => jump(l.number)}>
                  <span className="mr-2 tabular-nums text-danger">第 {l.number} 行</span>
                  {l.raw.trim()}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex min-h-0 flex-col">
          <div className="flex h-9 shrink-0 items-center gap-2 border-b border-line px-4 text-xs text-muted">
            <span className="flex-1">变更预览 · 共 {entries.length} 句</span>
            <label className="flex cursor-pointer items-center gap-1.5">
              <input type="checkbox" className="accent-[var(--accent)]" checked={changesOnly} onChange={(e) => setChangesOnly(e.target.checked)} />
              只看变更
            </label>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto py-1 font-mono text-[13px] leading-6">
            {rows.map((row, i) =>
              changesOnly && row.kind === "same" ? null : (
                <div
                  key={i}
                  className={cx("flex gap-2 px-3", ROW[row.kind][1], row.kind !== "deleted" && "cursor-pointer hover:brightness-95")}
                  onClick={() => row.kind !== "deleted" && jump(row.entry.number)}
                >
                  <span className={cx("w-3 shrink-0 select-none", row.kind === "added" ? "text-ok" : row.kind === "deleted" ? "text-danger" : "text-warn")}>{ROW[row.kind][0]}</span>
                  <span className="w-10 shrink-0 text-right text-muted tabular-nums select-none">{row.kind === "added" ? "新" : `#${row.line.index}`}</span>
                  <span className="min-w-0 flex-1 [overflow-wrap:anywhere]">
                    {row.kind === "deleted" ? (
                      <span className="text-danger line-through decoration-danger/50">
                        [{row.line.speaker}] {row.line.text}
                      </span>
                    ) : (
                      <>
                        <span className="text-accent">[{row.entry.speaker}]</span> {row.entry.text}
                        {row.kind === "modified" && (
                          <span className="block text-xs text-muted line-through">
                            [{row.line.speaker}] {row.line.text}
                          </span>
                        )}
                      </>
                    )}
                  </span>
                  {row.kind !== "added" && row.line.takes.length > 0 && <span className="shrink-0 text-xs text-muted select-none">{row.line.takes.length} Take</span>}
                </div>
              ),
            )}
            {!rows.length && <p className="px-4 py-8 text-center font-sans text-muted">在左侧输入台本</p>}
            {changesOnly && !changed && rows.length > 0 && <p className="px-4 py-8 text-center font-sans text-muted">没有变更</p>}
          </div>
        </div>
      </div>
    </Modal>
  );
}
