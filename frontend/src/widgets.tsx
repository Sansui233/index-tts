import { useRef, useState } from "react";
import { ChevronDown, Plus, Sliders, Trash2, Upload } from "react-feather";
import { api, isAudio, upload, type Audio, type Binding, type Generation, type Role } from "./api";
import { PlayButton, Player } from "./player";
import { useAction, useLoad } from "./state";
import { cx, Field, Segmented } from "./ui";

type Source = { name: string; path: string };
const SAMPLE = "sample:";

/* Reference audio: pick an imported file, import from samples/, or upload. */
export function AudioPicker({ value, onChange, exclude = [], all = false }: { value: string | null; onChange: (id: string, record?: Audio) => void; exclude?: string[]; all?: boolean }) {
  const audio = useLoad<Audio[]>(all ? "/audio" : "/audio?reference=true", []);
  const samples = useLoad<Source[]>("/audio/sources", []);
  const run = useAction();
  const file = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function add(fn: () => Promise<Audio>) {
    setBusy(true);
    const created = await run(fn);
    setBusy(false);
    if (!created) return;
    audio.setData((items) => [created, ...items]);
    onChange(created.id, created);
  }
  return (
    <div className="space-y-2">
      <div className="flex gap-1.5">
        <select
          className="input"
          aria-label="参考音频"
          value={value || ""}
          disabled={busy}
          onChange={(e) => {
            const v = e.target.value;
            if (v.startsWith(SAMPLE)) void add(() => api.post<Audio>("/audio/import", { path: v.slice(SAMPLE.length) }));
            else if (v) onChange(v, audio.data.find((a) => a.id === v));
          }}
        >
          <option value="">{busy ? "导入中…" : "选择参考音频…"}</option>
          <optgroup label="已导入">
            {audio.data
              .filter((a) => isAudio(a) && !exclude.includes(a.id))
              .map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
          </optgroup>
          {samples.data.length > 0 && (
            <optgroup label="samples（选择即导入）">
              {samples.data.map((s) => (
                <option key={s.path} value={SAMPLE + s.path}>
                  {s.name}
                </option>
              ))}
            </optgroup>
          )}
        </select>
        <button className="btn btn-icon" title="上传音频" aria-label="上传音频" disabled={busy} onClick={() => file.current?.click()}>
          <Upload size={14} />
        </button>
        <input
          ref={file}
          type="file"
          accept="audio/*"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0];
            e.target.value = "";
            if (f) void add(() => upload(f));
          }}
        />
      </div>
      {value && <Player id={value} />}
    </div>
  );
}

const NUMBERS: [keyof Generation, string, number][] = [
  ["temperature", "Temperature", 0.1],
  ["top_p", "Top P", 0.05],
  ["top_k", "Top K", 1],
  ["num_beams", "Beams", 1],
  ["repetition_penalty", "重复惩罚", 0.5],
  ["length_penalty", "长度惩罚", 0.1],
  ["max_mel_tokens", "Max mel tokens", 10],
  ["max_text_tokens_per_sentence", "分句最大 tokens", 10],
  ["sentences_bucket_max_size", "批次大小", 1],
];

export function GenerationParams({ value, onChange, open: initial = false }: { value: Generation; onChange: (g: Generation) => void; open?: boolean }) {
  const [open, setOpen] = useState(initial);
  const set = (patch: Partial<Generation>) => onChange({ ...value, ...patch });
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <Segmented
          value={value.mode}
          onChange={(mode) => set({ mode })}
          options={[
            { value: "normal", label: "普通推理" },
            { value: "fast", label: "批次推理", title: "长文本更快" },
          ]}
        />
        <button className="btn btn-ghost btn-sm" onClick={() => setOpen(!open)}>
          <Sliders size={13} />
          高级参数
          <ChevronDown size={13} className={cx("transition-transform", open && "rotate-180")} />
        </button>
      </div>
      {open && (
        <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2.5 sm:grid-cols-3">
          <label className="col-span-full flex cursor-pointer items-center gap-2 text-xs">
            <input type="checkbox" className="accent-[var(--accent)]" checked={value.do_sample} onChange={(e) => set({ do_sample: e.target.checked })} />
            启用采样（do_sample）
          </label>
          {NUMBERS.filter(([key]) => key !== "sentences_bucket_max_size" || value.mode === "fast").map(([key, label, step]) => (
            <Field key={key} label={label}>
              <input className="input h-7 tabular-nums" type="number" step={step} value={value[key] as number} onChange={(e) => set({ [key]: Number(e.target.value) })} />
            </Field>
          ))}
        </div>
      )}
    </div>
  );
}

/* Speaker name → role + reference audio. */
export function Bindings({ value, onChange, roles, audio }: { value: Binding[]; onChange: (v: Binding[]) => void; roles: Role[]; audio: Audio[] }) {
  const update = (index: number, patch: Partial<Binding>) => onChange(value.map((b, i) => (i === index ? { ...b, ...patch } : b)));
  const names = new Map(audio.map((a) => [a.id, a.name]));
  return (
    <div className="space-y-1.5">
      {value.length > 0 && (
        <div className="grid grid-cols-[1fr_1fr_1.4fr_24px_32px] gap-1.5 px-0.5 text-[11px] font-medium text-muted">
          <span>文本中的说话人</span>
          <span>角色</span>
          <span>参考音频</span>
        </div>
      )}
      {value.map((b, i) => {
        const role = roles.find((r) => r.id === b.role_id);
        const choices = role ? role.audio_ids : audio.map((a) => a.id);
        return (
          <div key={i} className="grid grid-cols-[1fr_1fr_1.4fr_24px_32px] items-center gap-1.5">
            <input className={cx("input", !b.speaker.trim() && "border-warn/60")} placeholder="如：旁白" value={b.speaker} onChange={(e) => update(i, { speaker: e.target.value })} />
            <select
              className="input"
              value={b.role_id || ""}
              onChange={(e) => {
                const r = roles.find((r) => r.id === e.target.value);
                update(i, { role_id: r?.id || null, audio_id: r?.audio_ids[0] || null });
              }}
            >
              <option value="">不使用角色</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
            <select className={cx("input", !b.audio_id && "border-warn/60")} value={b.audio_id || ""} onChange={(e) => update(i, { audio_id: e.target.value || null })}>
              <option value="">未绑定</option>
              {choices.map((id) => (
                <option key={id} value={id}>
                  {names.get(id) || id.slice(0, 8)}
                </option>
              ))}
            </select>
            <PlayButton id={b.audio_id} />
            <button className="btn btn-ghost btn-icon btn-danger" aria-label="移除" onClick={() => onChange(value.filter((_, n) => n !== i))}>
              <Trash2 size={14} />
            </button>
          </div>
        );
      })}
      <button className="btn btn-ghost btn-sm" onClick={() => onChange([...value, { speaker: "", role_id: null, audio_id: null }])}>
        <Plus size={13} />
        添加说话人
      </button>
    </div>
  );
}
