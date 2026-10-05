import { useState, type ReactNode } from "react";
import { Info, X } from "react-feather";
import { api, isActive, resultAudio, taskTitle, type Task } from "./api";
import { Player, SrtPreview } from "./player";
import { useAction } from "./state";
import { CopyButton, cx, Modal, Progress } from "./ui";

const STATUS: Record<Task["status"], [string, string]> = {
  queued: ["排队", "text-muted"],
  running: ["运行中", "text-accent"],
  succeeded: ["完成", "text-ok"],
  failed: ["失败", "text-danger"],
  cancelled: ["已取消", "text-muted"],
  interrupted: ["已中断", "text-warn"],
};
const KIND: Record<string, string> = { speech: "语音", subtitles: "字幕", "session-generate": "对话", merge: "合并", "model-load": "加载模型", "model-unload": "卸载模型" };
// The chip already says everything about model tasks.
const UNTITLED = new Set(["model-load", "model-unload"]);

const time = (iso?: string) => (iso ? new Date(iso).toLocaleString() : "—");
const report = (t: Task) => [`[${KIND[t.kind] || t.kind}] ${taskTitle(t) || "—"}`, t.error || t.message, `task ${t.id} · ${time(t.created_at)}`].join("\n");

interface Props {
  task: Task;
  /* Selection mode: a checkbox replaces the actions; active tasks cannot be selected. */
  selecting?: boolean;
  selected?: boolean;
  onSelect?: () => void;
}

export function TaskItem({ task, selecting, selected, onSelect }: Props) {
  const run = useAction();
  const [detail, setDetail] = useState(false);
  const [label, color] = STATUS[task.status];
  const audio = resultAudio(task);
  const title = UNTITLED.has(task.kind) ? "" : taskTitle(task);
  const selectable = selecting && !isActive(task);
  return (
    <div className={cx("flex gap-2.5 py-2.5", selectable && "cursor-pointer", selecting && !selectable && "opacity-50")} onClick={selectable ? onSelect : undefined}>
      {selecting && <input type="checkbox" className="mt-1 accent-[var(--accent)]" disabled={!selectable} checked={!!selected} onChange={onSelect} onClick={(e) => e.stopPropagation()} aria-label="选择任务" />}
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="chip">{KIND[task.kind] || task.kind}</span>
          <span className="group flex min-w-0 flex-1 items-center gap-1">
            <span className={cx("min-w-0 truncate font-medium", !title && "text-muted")}>{title || "—"}</span>
            {!selecting && (
              <button className="shrink-0 cursor-pointer text-muted opacity-0 transition-opacity group-hover:opacity-100 hover:text-accent focus-visible:opacity-100" aria-label="任务详情" title="任务详情" onClick={() => setDetail(true)}>
                <Info size={13} />
              </button>
            )}
          </span>
          <span className={cx("text-xs", color)}>{label}</span>
          {!selecting && isActive(task) && (
            <button className="btn btn-ghost btn-sm btn-icon" title="取消" onClick={() => void run(() => api.post(`/tasks/${task.id}/cancel`))}>
              <X size={13} />
            </button>
          )}
        </div>
        {isActive(task) && <Progress value={task.progress} />}
        {(isActive(task) || task.error) && (
          <div className="flex items-start gap-1">
            <p className={cx("min-w-0 flex-1 text-xs", task.error ? "line-clamp-3 text-danger [overflow-wrap:anywhere]" : "truncate text-muted")}>{task.error || task.message}</p>
            {task.status === "failed" && !selecting && <CopyButton className="-my-1" text={report(task)} label="复制错误信息" />}
          </div>
        )}
        {audio && <div onClick={(e) => selecting && e.stopPropagation()}>{audio.path.endsWith(".srt") ? <SrtPreview id={audio.id} /> : <Player id={audio.id} rename />}</div>}
      </div>
      {detail && <TaskDetail task={task} onClose={() => setDetail(false)} />}
    </div>
  );
}

function TaskDetail({ task, onClose }: { task: Task; onClose: () => void }) {
  const [label, color] = STATUS[task.status];
  const audio = resultAudio(task);
  const rows: [string, ReactNode][] = [
    ["类型", KIND[task.kind] || task.kind],
    ["状态", <span className={color}>{label}</span>],
    ["标题", <span className="[overflow-wrap:anywhere]">{taskTitle(task) || "—"}</span>],
    ["进度", `${Math.round(task.progress * 100)}%`],
    [task.error ? "错误" : "消息", <span className={cx("whitespace-pre-wrap [overflow-wrap:anywhere]", task.error && "text-danger")}>{task.error || task.message || "—"}</span>],
    ["创建", time(task.created_at)],
    ["开始", time(task.started_at)],
    ["结束", time(task.finished_at)],
    ["结果", audio ? <span className="[overflow-wrap:anywhere]">{audio.name}</span> : "—"],
    ["任务 ID", <span className="font-mono text-xs">{task.id}</span>],
  ];
  return (
    <Modal title="任务详情" onClose={onClose} actions={<CopyButton text={report(task)} label="复制详情" />}>
      <dl className="grid grid-cols-[64px_minmax(0,1fr)] gap-x-3 gap-y-2">
        {rows.map(([name, value]) => (
          <div key={name} className="contents">
            <dt className="text-muted">{name}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </Modal>
  );
}
