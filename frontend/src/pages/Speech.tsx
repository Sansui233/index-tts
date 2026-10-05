import { Mic } from "react-feather";
import { api, defaultGeneration, type Generation, type Task } from "../api";
import { TaskItem } from "../TaskItem";
import { useAction, useApp, useStored } from "../state";
import { Empty, Page, PageHeader, Section, Spinner } from "../ui";
import { AudioPicker, GenerationParams } from "../widgets";

export function Speech() {
  const { tasks, track } = useApp();
  const run = useAction();
  const [form, setForm] = useStored<{ text: string; audio: string | null; generation: Generation }>("speech", {
    text: "",
    audio: null,
    generation: defaultGeneration,
  });
  const recent = tasks.filter((t) => t.kind === "speech").slice(0, 12);
  const pending = recent.some((t) => t.status === "running" || t.status === "queued");

  async function submit() {
    const task = await run(() => api.post<Task>("/speech", { text: form.text, audio_id: form.audio, generation: form.generation }));
    if (task) track(task);
  }
  return (
    <Page>
      <PageHeader title="语音生成" sub="选择参考音频，把文本合成为语音" />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0 space-y-4">
          <section className="card overflow-hidden focus-within:border-accent/50">
            <textarea
              className="block min-h-56 w-full resize-y bg-transparent px-4 py-3.5 text-[14px] leading-relaxed outline-none placeholder:text-muted/70"
              placeholder="在这里输入要合成的文字…"
              value={form.text}
              onChange={(e) => setForm({ ...form, text: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && (e.ctrlKey || e.metaKey) && form.audio && form.text.trim() && void submit()}
            />
            <div className="flex items-center gap-3 border-t border-line bg-panel px-3 py-2">
              <span className="text-xs text-muted tabular-nums">{form.text.length} 字</span>
              <span className="hidden text-xs text-muted sm:inline">Ctrl + Enter 生成</span>
              <span className="flex-1" />
              {!form.audio && <span className="text-xs text-warn">请先选择参考音频</span>}
              <button className="btn btn-primary" disabled={!form.audio || !form.text.trim()} onClick={() => void submit()}>
                {pending ? <Spinner className="border-accent-fg/30 border-t-accent-fg" /> : <Mic size={14} />}
                生成语音
              </button>
            </div>
          </section>
          <Section title="最近生成" extra={<span className="text-xs text-muted">{recent.length} 条</span>}>
            {recent.length ? (
              <div className="-my-2.5 divide-y divide-line">
                {recent.map((t) => (
                  <TaskItem key={t.id} task={t} />
                ))}
              </div>
            ) : (
              <Empty title="还没有生成记录">生成的音频会出现在这里</Empty>
            )}
          </Section>
        </div>
        <div className="space-y-4">
          <Section title="参考音频">
            <AudioPicker value={form.audio} onChange={(audio) => setForm({ ...form, audio })} />
          </Section>
          <Section title="推理参数">
            <GenerationParams value={form.generation} onChange={(generation) => setForm({ ...form, generation })} />
          </Section>
        </div>
      </div>
    </Page>
  );
}
