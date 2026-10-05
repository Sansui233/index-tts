import { useEffect, useState } from "react";
import { api, fileUrl, type Audio, type Generation } from "./api";

export function Player({ id }: { id: string | null | undefined }) {
  return id ? (
    <div className="player">
      <audio controls preload="none" src={fileUrl(id)} />
      <a href={fileUrl(id, true)}>下载</a>
    </div>
  ) : (
    <span className="muted">尚无音频</span>
  );
}

export function AudioPicker({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (id: string) => void;
}) {
  const [items, setItems] = useState<Audio[]>([]),
    [sources, setSources] = useState<{ name: string; path: string }[]>([]),
    [source, setSource] = useState(""),
    [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    api<Audio[]>("/audio", "GET", undefined, c.signal)
      .then(setItems)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, []);
  async function add(file: File) {
    try {
      setError("");
      const data = new FormData();
      data.append("file", file);
      const a = await api<Audio>("/audio/upload", "POST", data);
      setItems((x) => [a, ...x]);
      onChange(a.id);
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <div className="stack">
      <select
        aria-label="参考音频"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">选择音频</option>
        {items
          .filter((a) => !a.path.endsWith(".srt"))
          .map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
      </select>
      <div className="row">
        <label className="button">
          上传音频
          <input
            type="file"
            accept="audio/*"
            hidden
            onChange={(e) => {
              if (e.target.files?.[0]) void add(e.target.files[0]);
            }}
          />
        </label>
        <button
          onClick={() =>
            api<{ name: string; path: string }[]>("/audio/sources")
              .then(setSources)
              .catch((e) => setError(e.message))
          }
        >
          浏览 samples
        </button>
      </div>
      {sources.length > 0 && (
        <div className="row">
          <select
            aria-label="samples 音频"
            value={source}
            onChange={(e) => setSource(e.target.value)}
          >
            <option value="">选择本地参考音频</option>
            {sources.map((a) => (
              <option key={a.path} value={a.path}>
                {a.name}
              </option>
            ))}
          </select>
          <button
            disabled={!source}
            onClick={async () => {
              try {
                const a = await api<Audio>("/audio/import", "POST", {
                  path: source,
                });
                setItems((x) => [a, ...x]);
                onChange(a.id);
                setSources([]);
              } catch (e) {
                setError(String(e));
              }
            }}
          >
            导入
          </button>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

export function Advanced({
  value,
  onChange,
}: {
  value: Generation;
  onChange: (g: Generation) => void;
}) {
  const labels: Record<string, string> = {
    top_p: "Top P",
    top_k: "Top K",
    temperature: "Temperature",
    length_penalty: "Length penalty",
    num_beams: "Beams",
    repetition_penalty: "Repetition penalty",
    max_mel_tokens: "Max mel tokens",
    max_text_tokens_per_sentence: "每段最大 tokens",
    sentences_bucket_max_size: "Batch size",
  };
  return (
    <details>
      <summary>生成参数</summary>
      <div className="grid-fields">
        <label>
          推理模式
          <select
            value={value.mode}
            onChange={(e) =>
              onChange({ ...value, mode: e.target.value as Generation["mode"] })
            }
          >
            <option value="normal">普通推理</option>
            <option value="fast">批次推理</option>
          </select>
        </label>
        <label className="row">
          <input
            type="checkbox"
            checked={value.do_sample}
            onChange={(e) =>
              onChange({ ...value, do_sample: e.target.checked })
            }
          />
          采样
        </label>
        {Object.entries(labels).map(([key, label]) => (
          <label key={key}>
            {label}
            <input
              type="number"
              step="any"
              value={value[key as keyof Generation] as number}
              onChange={(e) =>
                onChange({ ...value, [key]: Number(e.target.value) })
              }
            />
          </label>
        ))}
      </div>
    </details>
  );
}

export function Cleanup({
  path,
  onDone,
}: {
  path: string;
  onDone: () => void;
}) {
  const [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <span>
      <button
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            const result = await api<{
              deleted: number;
              bytes: number;
              failures: unknown[];
            }>(path + "/takes/cleanup", "POST");
            setMessage(
              `已清理 ${result.deleted} 个 Take，释放 ${(result.bytes / 1048576).toFixed(1)} MB${result.failures.length ? `；${result.failures.length} 项失败，请重试` : ""}`,
            );
            onDone();
          } catch (e) {
            setMessage(String(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        清理未使用 Take
      </button>
      {message && <small role="status">{message}</small>}
    </span>
  );
}
