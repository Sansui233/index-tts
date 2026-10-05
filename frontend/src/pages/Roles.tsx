import { useMemo, useState, type MouseEvent } from "react";
import { Plus, Search, Trash2, Users } from "react-feather";
import { api, type Audio, type Role } from "../api";
import { Player } from "../player";
import { useAction, useLoad } from "../state";
import { confirm, cx, Empty, Field, Page, PageHeader, Sheet } from "../ui";
import { AudioPicker } from "../widgets";

type Draft = { id?: string; name: string; tags: string; audio_ids: string[] };
const toDraft = (r?: Role): Draft => ({ id: r?.id, name: r?.name || "", tags: r?.tags.join(", ") || "", audio_ids: r?.audio_ids || [] });

export function Avatar({ name, className }: { name: string; className?: string }) {
  return (
    <span className={cx("grid size-9 shrink-0 place-items-center rounded-full bg-accent-soft font-semibold text-accent", className)}>
      {name.trim().slice(0, 1) || "?"}
    </span>
  );
}

export function Roles() {
  const roles = useLoad<Role[]>("/roles", []);
  const audio = useLoad<Audio[]>("/audio?reference=true", []);
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState<Draft | null>(null);
  const names = useMemo(() => new Map(audio.data.map((a) => [a.id, a.name])), [audio.data]);
  const q = query.trim().toLowerCase();
  const shown = roles.data
    .filter((r) => !q || r.name.toLowerCase().includes(q) || r.tags.some((t) => t.toLowerCase().includes(q)))
    .sort((a, b) => a.name.localeCompare(b.name, "zh"));

  return (
    <Page wide>
      <PageHeader title="角色管理" sub={`${roles.data.length} 个角色 · 名称、标签与参考音频集合`}>
        <div className="relative">
          <Search size={13} className="absolute top-2.5 left-2.5 text-muted" />
          <input className="input w-52 pl-7" placeholder="搜索名称或标签" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={() => setDraft(toDraft())}>
          <Plus size={14} />
          新建角色
        </button>
      </PageHeader>
      {shown.length ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-3">
          {shown.map((r) => (
            <div key={r.id} role="button" tabIndex={0} onClick={() => setDraft(toDraft(r))} className="card flex cursor-pointer flex-col gap-2.5 p-3 text-left transition-colors hover:border-accent/40 hover:bg-panel">
              <div className="flex items-center gap-2.5">
                <Avatar name={r.name} />
                <div className="min-w-0">
                  <p className="truncate font-medium">{r.name}</p>
                  <p className="text-xs text-muted">{r.audio_ids.length} 段参考音频</p>
                </div>
              </div>
              <div className="flex min-h-5 flex-wrap gap-1">
                {r.tags.length ? r.tags.map((t) => <span key={t} className="chip">{t}</span>) : <span className="text-xs text-muted/60">无标签</span>}
              </div>
              <div onClick={(e) => e.stopPropagation()}>
                <Player id={r.audio_ids[0]} download={false} />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <Empty icon={<Users size={18} />} title={q ? "没有匹配的角色" : "还没有角色"}>
          {!q && "角色保存一组参考音频，可在多人对话中复用"}
        </Empty>
      )}
      {draft && (
        <RoleEditor
          draft={draft}
          names={names}
          onClose={() => setDraft(null)}
          onSaved={() => {
            setDraft(null);
            void roles.reload();
            void audio.reload();
          }}
        />
      )}
    </Page>
  );
}

function RoleEditor({ draft: initial, names, onClose, onSaved }: { draft: Draft; names: Map<string, string>; onClose: () => void; onSaved: () => void }) {
  const run = useAction();
  const [draft, setDraft] = useState(initial);
  const [labels, setLabels] = useState(names);
  const [renamed, setRenamed] = useState<Record<string, string>>({});

  async function save() {
    const body = { name: draft.name, tags: draft.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean), audio_ids: draft.audio_ids };
    const ok = await run(async () => {
      for (const [id, name] of Object.entries(renamed)) if (name.trim() && name !== labels.get(id)) await api.patch(`/audio/${id}`, { name });
      await (draft.id ? api.put(`/roles/${draft.id}`, body) : api.post("/roles", body));
      return true;
    }, "角色已保存");
    if (ok) onSaved();
  }
  async function remove(e: MouseEvent) {
    if (!(await confirm(e, `删除角色「${draft.name}」？参考音频文件会保留。`))) return;
    if (await run(() => api.del(`/roles/${draft.id}`), "角色已删除")) onSaved();
  }
  return (
    <Sheet
      open
      onClose={onClose}
      title={draft.id ? "编辑角色" : "新建角色"}
      footer={
        <>
          {draft.id && (
            <button className="btn btn-ghost btn-danger" onClick={(e) => void remove(e)}>
              <Trash2 size={14} />
              删除
            </button>
          )}
          <span className="flex-1" />
          <button className="btn" onClick={onClose}>
            取消
          </button>
          <button className="btn btn-primary" disabled={!draft.name.trim()} onClick={() => void save()}>
            保存
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="flex items-end gap-3">
          <Avatar name={draft.name} className="size-11 text-lg" />
          <Field label="名称" className="flex-1">
            <input className="input" autoFocus value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          </Field>
        </div>
        <Field label="标签（逗号分隔）">
          <input className="input" placeholder="少女, 温柔" value={draft.tags} onChange={(e) => setDraft({ ...draft, tags: e.target.value })} />
        </Field>
        <div>
          <span className="label">参考音频 · {draft.audio_ids.length}</span>
          <div className="space-y-2">
            {draft.audio_ids.map((id) => (
              <div key={id} className="rounded-lg border border-line p-2">
                <div className="mb-1.5 flex items-center gap-1.5">
                  <input
                    className="input h-7 border-transparent bg-transparent px-1.5 font-medium hover:border-line"
                    value={renamed[id] ?? labels.get(id) ?? ""}
                    onChange={(e) => setRenamed({ ...renamed, [id]: e.target.value })}
                  />
                  <button className="btn btn-ghost btn-sm btn-icon btn-danger" title="移出角色" onClick={() => setDraft({ ...draft, audio_ids: draft.audio_ids.filter((x) => x !== id) })}>
                    <Trash2 size={13} />
                  </button>
                </div>
                <Player id={id} />
              </div>
            ))}
            <div className="rounded-lg border border-dashed border-line p-2">
              <AudioPicker value={null} exclude={draft.audio_ids} onChange={(id, record) => {
                  if (record) setLabels((m) => new Map(m).set(id, record.name));
                  setDraft((d) => ({ ...d, audio_ids: [...d.audio_ids, id] }));
                }} />
            </div>
          </div>
        </div>
      </div>
    </Sheet>
  );
}
