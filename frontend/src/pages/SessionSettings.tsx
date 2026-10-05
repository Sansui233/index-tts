import { Bookmark, Save } from "react-feather";
import { api, type Named, type Preset, type Role, type Session } from "../api";
import { useAction, useLoad } from "../state";
import { ask, Field } from "../ui";
import { Bindings, GenerationParams } from "../widgets";

type Draft = Pick<Session, "name" | "project_id" | "interval" | "bindings" | "generation">;
export const toDraft = ({ name, project_id, interval, bindings, generation }: Session): Draft => ({ name, project_id, interval, bindings, generation });

export function SessionSettings({ draft, setDraft, session, projects, onSaved }: { draft: Draft; setDraft: (d: Draft) => void; session: Session; projects: Named[]; onSaved: (s: Session) => void }) {
  const run = useAction();
  const roles = useLoad<Role[]>("/roles", []);
  const dirty = JSON.stringify(draft) !== JSON.stringify(toDraft(session));

  async function savePreset() {
    const values = await ask("保存为多人预设", [{ key: "name", label: "预设名称（同名则覆盖）", value: draft.name }], "保存");
    if (!values) return;
    const body = { name: values.name, bindings: draft.bindings, generation: draft.generation };
    await run(async () => {
      const existing = (await api.get<Preset[]>("/presets")).find((p) => p.name === values.name);
      return existing ? api.put<Preset>(`/presets/${existing.id}`, body) : api.post<Preset>("/presets", body);
    }, "预设已保存");
  }
  async function save() {
    const saved = await run(() => api.put<Session>(`/sessions/${session.id}`, draft), "设置已保存");
    if (saved) onSaved(saved);
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
      <div className="space-y-4">
        <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_96px] gap-2">
          <Field label="名称">
            <input className="input" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          </Field>
          <Field label="所属项目">
            <select className="input" value={draft.project_id} onChange={(e) => setDraft({ ...draft, project_id: e.target.value })}>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="句间隔（秒）">
            <input className="input tabular-nums" type="number" min={0} max={30} step={0.1} value={draft.interval} onChange={(e) => setDraft({ ...draft, interval: Number(e.target.value) })} />
          </Field>
        </div>
        <div>
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <span className="label mb-0">说话人绑定</span>
            <button className="btn btn-ghost btn-sm" title="同名预设会被覆盖" disabled={!draft.bindings.length} onClick={() => void savePreset()}>
              <Bookmark size={13} />
              存为预设
            </button>
          </div>
          <Bindings value={draft.bindings} onChange={(bindings) => setDraft({ ...draft, bindings })} roles={roles.data} />
        </div>
      </div>
      <div className="flex flex-col gap-4">
        <div>
          <span className="label">推理参数</span>
          <GenerationParams open value={draft.generation} onChange={(generation) => setDraft({ ...draft, generation })} />
        </div>
        <div className="mt-auto flex justify-end gap-2">
          <button className="btn" disabled={!dirty} onClick={() => setDraft(toDraft(session))}>
            还原
          </button>
          <button className="btn btn-primary" disabled={!dirty || !draft.name.trim()} onClick={() => void save()}>
            <Save size={14} />
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
}
