import { useState } from "react";
import { api, defaults, type Task } from "../api";
import { Advanced, AudioPicker, Player } from "../components";

export function Speech({
  subtitle = false,
  onTask,
}: {
  subtitle?: boolean;
  onTask: (t: Task) => void;
}) {
  const [audio, setAudio] = useState<string | null>(null),
    [text, setText] = useState(""),
    [generation, setGeneration] = useState(defaults),
    [model, setModel] = useState("base"),
    [language, setLanguage] = useState("zh"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <section className="page">
      <header>
        <p className="eyebrow">工作台 / {subtitle ? "字幕" : "语音"}</p>
        <h1>{subtitle ? "字幕生成" : "语音生成"}</h1>
        <p className="muted">
          {subtitle
            ? "选择音频，生成可下载的 SRT 字幕。"
            : "选择一个声音，让文字成为语音。"}
        </p>
      </header>
      <div className="card stack">
        <h2>{subtitle ? "输入音频" : "参考音频"}</h2>
        <AudioPicker value={audio} onChange={setAudio} />
        <Player id={audio} />
        {subtitle ? (
          <div className="grid-fields">
            <label>
              Whisper 模型
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {["tiny", "base", "small", "medium"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              语言
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="zh">中文</option>
                <option value="en">English</option>
                <option value="ja">日本語</option>
              </select>
            </label>
          </div>
        ) : (
          <>
            <label>
              生成文本
              <textarea
                rows={8}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="在这里输入文字…"
              />
            </label>
            <Advanced value={generation} onChange={setGeneration} />
          </>
        )}
        <div className="row">
          <button
            className="primary"
            disabled={busy || !audio || (!subtitle && !text.trim())}
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                onTask(
                  await api<Task>(
                    subtitle ? "/subtitles" : "/speech",
                    "POST",
                    subtitle
                      ? { audio_id: audio, model, language }
                      : { audio_id: audio, text, generation },
                  ),
                );
              } catch (e) {
                setError(String(e));
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "正在提交…" : subtitle ? "生成字幕" : "生成语音"}
          </button>
          <span className="muted">结果将在任务面板中显示</span>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}
