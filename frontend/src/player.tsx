import { useEffect, useState, useSyncExternalStore, type MouseEvent } from "react";
import { Download, Edit2, Pause, Play } from "react-feather";
import { api, fileUrl, type Audio } from "./api";
import { useAction } from "./state";
import { cx, point, promptAt } from "./ui";

/* One shared <audio>: starting a clip stops the previous one, and rows stay cheap. */
const audio = new Audio();
let state = { id: "", playing: false, time: 0, duration: 0 };
const listeners = new Set<() => void>();
const emit = (patch: Partial<typeof state>) => {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
};
audio.addEventListener("timeupdate", () => emit({ time: audio.currentTime }));
audio.addEventListener("loadedmetadata", () => emit({ duration: audio.duration }));
audio.addEventListener("play", () => emit({ playing: true }));
audio.addEventListener("pause", () => emit({ playing: false }));
audio.addEventListener("ended", () => emit({ playing: false, time: 0 }));

function toggle(id: string) {
  if (state.id !== id) {
    audio.src = fileUrl(id);
    emit({ id, time: 0, duration: 0 });
  }
  void (audio.paused ? audio.play() : audio.pause());
}

const subscribe = (l: () => void) => (listeners.add(l), () => void listeners.delete(l));
const clock = (s: number) => (isFinite(s) ? `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}` : "0:00");

/* Audio preview + file actions. `rename` adds the rename button beside download. */
export function Player({ id, download = true, rename = false, className }: { id?: string | null; download?: boolean; rename?: boolean; className?: string }) {
  const s = useSyncExternalStore(subscribe, () => state);
  if (!id) return <span className={cx("text-xs text-muted", className)}>未生成</span>;
  const active = s.id === id;
  const ratio = active && s.duration ? s.time / s.duration : 0;
  return (
    <div className={cx("flex h-8 min-w-0 items-center gap-2 rounded-full bg-hover pr-2 pl-1", className)}>
      <PlayButton id={id} />
      <div
        className="relative h-1 min-w-10 flex-1 cursor-pointer rounded-full bg-line"
        onClick={(e) => {
          if (!active || !s.duration) return;
          const box = e.currentTarget.getBoundingClientRect();
          audio.currentTime = ((e.clientX - box.left) / box.width) * s.duration;
        }}
      >
        <div className="absolute inset-y-0 left-0 rounded-full bg-accent" style={{ width: `${ratio * 100}%` }} />
      </div>
      <span className="shrink-0 text-[11px] text-muted tabular-nums">{active ? `${clock(s.time)} / ${clock(s.duration)}` : "—:——"}</span>
      <FileActions id={id} download={download} rename={rename} />
    </div>
  );
}

/* Subtitle preview: first cue as a one-line excerpt, then the same file actions as Player. */
export function SrtPreview({ id, className }: { id: string; className?: string }) {
  const [excerpt, setExcerpt] = useState("");
  useEffect(() => {
    let live = true;
    fetch(fileUrl(id))
      .then((r) => (r.ok ? r.text() : ""))
      .then((text) => live && setExcerpt(firstCue(text)))
      .catch(() => {});
    return () => void (live = false);
  }, [id]);
  return (
    <div className={cx("flex h-8 min-w-0 items-center gap-2 rounded-full bg-hover pr-2 pl-3", className)}>
      <span className="chip shrink-0 bg-bg">SRT</span>
      <span className={cx("min-w-0 flex-1 truncate text-xs", !excerpt && "text-muted")} title={excerpt}>
        {excerpt || "（空字幕）"}
      </span>
      <FileActions id={id} rename />
    </div>
  );
}

/* Text of the first SRT block: skip the number and the timing line. */
function firstCue(srt: string) {
  const block = srt.replace(/\r/g, "").trim().split(/\n\s*\n/)[0] || "";
  return block
    .split("\n")
    .filter((line) => line.trim() && !/^\d+$/.test(line.trim()) && !line.includes("-->"))
    .join(" ");
}

/* Rename (popover at the pointer, extension kept) and download. Renaming changes only the
   download name in the audio record; the file on disk and all references keep the id. */
function FileActions({ id, download = true, rename = false }: { id: string; download?: boolean; rename?: boolean }) {
  const run = useAction();
  async function renameFile(e: MouseEvent) {
    const at = point(e);
    const record = await run(() => api.get<Audio>(`/audio/${id}`));
    if (!record) return;
    // Generated audio has a display name without extension; a real file name keeps its own.
    const suffix = record.path.slice(record.path.lastIndexOf("."));
    const ext = record.name.toLowerCase().endsWith(suffix.toLowerCase()) ? record.name.slice(-suffix.length) : "";
    const stem = record.name.slice(0, record.name.length - ext.length);
    const next = await promptAt(at, `重命名${ext ? `（保留 ${ext}）` : ""}`, stem, "重命名");
    const clean = next?.replace(/[\\/:*?"<>|]+/g, " ").trim();
    if (!clean || clean === stem) return;
    await run(() => api.patch(`/audio/${id}`, { name: clean + ext }), "已重命名");
  }
  return (
    <>
      {rename && (
        <button className="shrink-0 cursor-pointer text-muted hover:text-accent" aria-label="重命名" title="重命名" onClick={(e) => void renameFile(e)}>
          <Edit2 size={13} />
        </button>
      )}
      {download && (
        <a href={fileUrl(id, true)} className="shrink-0 text-muted hover:text-accent" aria-label="下载" title="下载">
          <Download size={13} />
        </a>
      )}
    </>
  );
}

/* Play/pause only, for previews in dense rows. */
export function PlayButton({ id, className }: { id?: string | null; className?: string }) {
  const s = useSyncExternalStore(subscribe, () => state);
  const playing = !!id && s.id === id && s.playing;
  return (
    <button
      disabled={!id}
      onClick={() => id && toggle(id)}
      aria-label={playing ? "暂停" : "试听"}
      title={playing ? "暂停" : "试听"}
      className={cx(
        "grid size-6 shrink-0 cursor-pointer place-items-center rounded-full bg-accent text-accent-fg transition-transform hover:scale-105 disabled:cursor-default disabled:bg-line disabled:text-muted disabled:hover:scale-100",
        className,
      )}
    >
      {playing ? <Pause size={11} fill="currentColor" /> : <Play size={11} fill="currentColor" className="ml-px" />}
    </button>
  );
}
