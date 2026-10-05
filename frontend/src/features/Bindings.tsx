import { type Binding, type Role, type Audio } from "../api";

export function Bindings({
  value,
  onChange,
  roles,
  audio,
}: {
  value: Binding[];
  onChange: (v: Binding[]) => void;
  roles: Role[];
  audio: Audio[];
}) {
  function update(index: number, patch: Partial<Binding>) {
    onChange(value.map((b, i) => (i === index ? { ...b, ...patch } : b)));
  }
  return (
    <div className="stack">
      {value.map((b, i) => (
        <div className="binding" key={i}>
          <input
            aria-label="说话人"
            placeholder="文本中的角色名"
            value={b.speaker}
            onChange={(e) => update(i, { speaker: e.target.value })}
          />
          <select
            aria-label="角色预设"
            value={b.role_id || ""}
            onChange={(e) => {
              const r = roles.find((r) => r.id === e.target.value);
              update(i, {
                role_id: r?.id || null,
                audio_id: r?.audio_ids[0] || null,
              });
            }}
          >
            <option value="">独立绑定</option>
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
          <select
            aria-label="角色参考音频"
            value={b.audio_id || ""}
            onChange={(e) => update(i, { audio_id: e.target.value || null })}
          >
            <option value="">未绑定音频</option>
            {audio
              .filter(
                (a) =>
                  !a.path.endsWith(".srt") &&
                  (!b.role_id ||
                    roles
                      .find((r) => r.id === b.role_id)
                      ?.audio_ids.includes(a.id)),
              )
              .map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
          </select>
          <button onClick={() => onChange(value.filter((_, n) => n !== i))}>
            移除
          </button>
        </div>
      ))}
      <button
        onClick={() =>
          onChange([...value, { speaker: "", role_id: null, audio_id: null }])
        }
      >
        ＋ 添加角色绑定
      </button>
    </div>
  );
}
