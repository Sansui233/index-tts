import { useEffect, useState } from "react";
import { api, type Line, type Task, type Generation } from "../api";
import { Cleanup, Player } from "../components";

export function LineEditor({
  line,
  sessionId,
  refresh,
  onTask,
  move,
  referenceId,
  generation,
}: {
  line: Line;
  sessionId: string;
  refresh: () => void;
  onTask: (t: Task) => void;
  move: (direction: number) => void;
  referenceId: string | null;
  generation: Generation;
}) {
  const [text, setText] = useState(line.text),
    [speaker, setSpeaker] = useState(line.speaker),
    [error, setError] = useState(""),
    [history, setHistory] = useState(false);
  useEffect(() => {
    setText(line.text);
    setSpeaker(line.speaker);
  }, [line.text, line.speaker]);
  const base = `/sessions/${sessionId}/lines/${line.id}`,
    current = line.takes.find((t) => t.id === line.current_take_id),
    dirty = text !== line.text || speaker !== line.speaker;
  const stale =
    current &&
    (current.snapshot.text !== line.text ||
      current.snapshot.speaker !== line.speaker ||
      current.snapshot.audio_id !== referenceId ||
      Object.keys(generation).some(
        (key) =>
          current.snapshot.generation[key as keyof Generation] !==
          generation[key as keyof Generation],
      ));
  async function action(fn: () => Promise<unknown>) {
    try {
      setError("");
      await fn();
      refresh();
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <article className="line-card">
      <div className="row between">
        <span className="index">#{line.index}</span>
        <div className="row">
          <button aria-label="上移句子" onClick={() => move(-1)}>
            ↑
          </button>
          <button aria-label="下移句子" onClick={() => move(1)}>
            ↓
          </button>
          <span className="badge">
            {current ? `当前 Take ${current.take_index}` : "未生成"}
          </span>
        </div>
      </div>
      <div className="line-content">
        <label>
          角色
          <input value={speaker} onChange={(e) => setSpeaker(e.target.value)} />
        </label>
        <label>
          文本
          <textarea
            rows={2}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
      </div>
      <div className="row">
        <button
          disabled={!dirty}
          onClick={() => action(() => api(base, "PUT", { text, speaker }))}
        >
          保存文本
        </button>
        <button
          className="primary"
          disabled={dirty}
          onClick={() =>
            action(async () =>
              onTask(await api<Task>(base + "/generate", "POST")),
            )
          }
        >
          生成新 Take
        </button>
        <button onClick={() => setHistory(!history)}>
          {line.takes.length} 个 Take {history ? "▴" : "▾"}
        </button>
        <button
          className="danger"
          onClick={() => {
            if (confirm("删除此句和全部 Take？"))
              void action(() => api(base, "DELETE"));
          }}
        >
          删除句子
        </button>
      </div>
      <Player id={current?.audio_id} />
      {stale && (
        <p className="warning">
          当前 Take 与已保存的文本、参考音频或生成参数不同
        </p>
      )}
      {history && (
        <div className="take-list">
          {line.takes.map((t) => (
            <div key={t.id} className="inset stack">
              <div className="row between">
                <strong>
                  Take {t.take_index}{" "}
                  {t.id === line.current_take_id ? "· 当前" : ""}
                </strong>
                <small>{new Date(t.created_at).toLocaleString()}</small>
                <button
                  disabled={t.id === line.current_take_id || !t.audio_id}
                  onClick={() =>
                    action(() =>
                      api(base + "/current-take", "PUT", { take_id: t.id }),
                    )
                  }
                >
                  设为当前
                </button>
              </div>
              <Player id={t.audio_id} />
              <details>
                <summary>生成时的文本</summary>
                <p>{t.snapshot.text}</p>
              </details>
            </div>
          ))}
          <Cleanup path={base} onDone={refresh} />
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </article>
  );
}
