import { Cpu, Database, Monitor, Moon, Sun } from "react-feather";
import { api, type Task } from "../api";
import { useAction, useApp, useLoad, useTheme } from "../state";
import { cx, Page, PageHeader, Section, Segmented } from "../ui";

const STATES: Record<string, [string, string]> = {
  loaded: ["已加载", "bg-ok"],
  loading: ["加载中", "bg-warn animate-pulse"],
  unloading: ["卸载中", "bg-warn animate-pulse"],
  unloaded: ["未加载", "bg-line"],
  error: ["加载失败", "bg-danger"],
};

export function Settings() {
  const { model, track } = useApp();
  const run = useAction();
  const [theme, setTheme] = useTheme();
  const info = useLoad<{ data_dir: string; subtitle_models: string[] }>("/settings", { data_dir: "", subtitle_models: [] });
  const [label, dot] = STATES[model] || [model, "bg-line"];
  const submit = async (path: string) => {
    const task = await run(() => api.post<Task>(path));
    if (task) track(task);
  };
  return (
    <Page>
      <PageHeader title="设置" />
      <div className="grid gap-4 md:grid-cols-2">
        <Section title={<span className="flex items-center gap-2"><Cpu size={14} className="text-accent" />IndexTTS 模型</span>}>
          <div className="mb-3 flex items-center gap-2">
            <span className={cx("size-2 rounded-full", dot)} />
            <span className="font-medium">{label}</span>
          </div>
          <p className="mb-4 text-xs leading-relaxed text-muted">生成时自动加载；显存不足时可手动卸载。卸载在当前推理结束后执行，字幕识别前会自动释放 TTS。</p>
          <div className="flex gap-2">
            <button className="btn btn-primary" disabled={model === "loaded" || model.endsWith("ing")} onClick={() => void submit("/models/load")}>
              加载模型
            </button>
            <button className="btn" disabled={model !== "loaded"} onClick={() => void submit("/models/unload")}>
              卸载模型
            </button>
          </div>
        </Section>
        <Section title={<span className="flex items-center gap-2"><Database size={14} className="text-accent" />存储与字幕</span>}>
          <dl className="grid grid-cols-[88px_minmax(0,1fr)] gap-y-2 text-xs">
            <dt className="text-muted">数据目录</dt>
            <dd className="font-mono break-all">{info.data.data_dir || "—"}</dd>
            <dt className="text-muted">Whisper 模型</dt>
            <dd className="flex flex-wrap gap-1">
              {info.data.subtitle_models.length ? info.data.subtitle_models.map((m) => <span key={m} className="chip chip-accent">{m}</span>) : <span className="text-muted">未找到（checkpoints/whisper）</span>}
            </dd>
          </dl>
        </Section>
        <Section title="外观">
          <Segmented
            value={theme}
            onChange={setTheme}
            options={[
              { value: "light", label: <><Sun size={13} />日间</> },
              { value: "dark", label: <><Moon size={13} />夜间</> },
              { value: "system", label: <><Monitor size={13} />跟随系统</> },
            ]}
          />
        </Section>
      </div>
    </Page>
  );
}
