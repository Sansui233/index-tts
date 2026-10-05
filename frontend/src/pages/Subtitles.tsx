import { FileText } from "react-feather";
import { api, type Task } from "../api";
import { TaskItem } from "../TaskItem";
import { useAction, useApp, useLoad, useStored } from "../state";
import { Empty, Field, Page, PageHeader, Section, Segmented } from "../ui";
import { AudioPicker } from "../widgets";

const LANGUAGES = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
];

export function Subtitles() {
  const { tasks, track } = useApp();
  const run = useAction();
  const settings = useLoad<{ subtitle_models: string[] }>("/settings", { subtitle_models: [] });
  const [form, setForm] = useStored<{ audio: string | null; model: string; language: string }>("subtitles", { audio: null, model: "base", language: "zh" });
  const models = settings.data.subtitle_models;
  const recent = tasks.filter((t) => t.kind === "subtitles").slice(0, 12);

  async function submit() {
    const task = await run(() => api.post<Task>("/subtitles", { audio_id: form.audio, model: form.model, language: form.language }));
    if (task) track(task);
  }
  return (
    <Page>
      <PageHeader title="字幕生成" sub="使用本地 Whisper 识别音频，导出 SRT 字幕" />
      <div className="grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]">
        <Section title="识别设置" className="h-fit space-y-4">
          <Field label="音频">
            <AudioPicker all value={form.audio} onChange={(audio) => setForm({ ...form, audio })} />
          </Field>
          <Field label="Whisper 模型">
            <select className="input" value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}>
              {["tiny", "base", "small", "medium"].map((m) => (
                <option key={m} value={m} disabled={!settings.loading && !models.includes(m)}>
                  {m}
                  {!settings.loading && !models.includes(m) ? "（未下载）" : ""}
                </option>
              ))}
            </select>
          </Field>
          <div>
            <span className="label">语言</span>
            <Segmented value={form.language} onChange={(language) => setForm({ ...form, language })} options={LANGUAGES} />
          </div>
          <button className="btn btn-primary w-full" disabled={!form.audio} onClick={() => void submit()}>
            <FileText size={14} />
            生成字幕
          </button>
        </Section>
        <Section title="字幕任务">
          {recent.length ? (
            <div className="-my-2.5 divide-y divide-line">
              {recent.map((t) => (
                <TaskItem key={t.id} task={t} />
              ))}
            </div>
          ) : (
            <Empty icon={<FileText size={18} />} title="还没有字幕任务">
              模型需放在 checkpoints/whisper/whisper-&#123;size&#125;
            </Empty>
          )}
        </Section>
      </div>
    </Page>
  );
}
