import { useEffect, useState } from "react";
import { api, type Audio, type Role } from "../api";
import { AudioPicker, Player } from "../components";

export function Roles() {
  const [roles, setRoles] = useState<Role[]>([]),
    [current, setCurrent] = useState<Role | null>(null),
    [name, setName] = useState(""),
    [tags, setTags] = useState(""),
    [audioIds, setAudioIds] = useState<string[]>([]),
    [error, setError] = useState("");
  const refresh = () =>
    api<Role[]>("/roles")
      .then(setRoles)
      .catch((e) => setError(e.message));
  useEffect(() => {
    void refresh();
  }, []);
  function edit(r: Role | null) {
    setCurrent(r);
    setName(r?.name || "");
    setTags(r?.tags.join(", ") || "");
    setAudioIds(r?.audio_ids || []);
  }
  return (
    <section className="page">
      <header>
        <p className="eyebrow">声音资源</p>
        <h1>角色管理</h1>
        <p className="muted">管理角色的参考音频与标签。</p>
      </header>
      <div className="two-panels">
        <div className="stack">
          <button onClick={() => edit(null)}>＋ 新建角色</button>
          {roles.map((r) => (
            <button
              key={r.id}
              className={
                "list-item " + (current?.id === r.id ? "selected" : "")
              }
              onClick={() => edit(r)}
            >
              <strong>{r.name}</strong>
              <small>
                {r.audio_ids.length} 个参考音频 ·{" "}
                {r.tags.join(" / ") || "无标签"}
              </small>
            </button>
          ))}
        </div>
        <div className="card stack">
          <h2>{current ? "编辑角色" : "新角色"}</h2>
          <label>
            名称
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            标签（逗号分隔）
            <input value={tags} onChange={(e) => setTags(e.target.value)} />
          </label>
          <h3>参考音频</h3>
          {audioIds.map((id) => (
            <RoleAudio
              key={id}
              id={id}
              remove={() => setAudioIds((x) => x.filter((i) => i !== id))}
            />
          ))}
          <AudioPicker
            value={null}
            onChange={(id) =>
              setAudioIds((x) => (x.includes(id) ? x : [...x, id]))
            }
          />
          <div className="row">
            <button
              className="primary"
              disabled={!name.trim()}
              onClick={async () => {
                try {
                  const r = await api<Role>(
                    current ? `/roles/${current.id}` : "/roles",
                    current ? "PUT" : "POST",
                    {
                      name,
                      tags: tags
                        .split(/[,，]/)
                        .map((x) => x.trim())
                        .filter(Boolean),
                      audio_ids: audioIds,
                    },
                  );
                  edit(r);
                  await refresh();
                  setError("");
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              保存角色
            </button>
            {current && (
              <button
                className="danger"
                onClick={async () => {
                  if (!confirm("删除这个角色？")) return;
                  try {
                    await api(`/roles/${current.id}`, "DELETE");
                    edit(null);
                    await refresh();
                  } catch (e) {
                    setError(String(e));
                  }
                }}
              >
                删除
              </button>
            )}
          </div>
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    </section>
  );
}

function RoleAudio({ id, remove }: { id: string; remove: () => void }) {
  const [name, setName] = useState("");
  return (
    <div className="inset stack">
      <Player id={id} />
      <div className="row">
        <input
          aria-label="音频名称"
          placeholder="新的音频名称"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button
          disabled={!name.trim()}
          onClick={() =>
            api<Audio>(`/audio/${id}`, "PATCH", { name })
              .then(() => setName(""))
              .catch((e) => alert(e.message))
          }
        >
          重命名
        </button>
        <button onClick={remove}>移除关联</button>
      </div>
    </div>
  );
}
