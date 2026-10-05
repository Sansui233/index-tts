import { useMemo, useState, type MouseEvent } from "react";
import { Folder, Plus, Search, Trash2, Users } from "react-feather";
import { api, type Audio, type Role } from "../api";
import { PlayButton, Player } from "../player";
import { useAction, useLoad } from "../state";
import { confirm, cx, Empty, Field, Page, PageHeader, Sheet } from "../ui";

type Draft = { id?: string; name: string; saved: string; tags: string; anonymous: boolean; audio_ids: string[] };
const toDraft = (r?: Role): Draft => ({ id: r?.id, name: r?.name || "", saved: r?.name || "", tags: r?.tags.join(", ") || "", anonymous: r?.anonymous ?? false, audio_ids: r?.audio_ids || [] });

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
    .sort((a, b) => Number(a.anonymous) - Number(b.anonymous) || a.name.localeCompare(b.name, "zh"));

  return (
    <Page wide>
      <PageHeader title="角色管理" sub={`${roles.data.length} 个角色`}>
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
        <div className="space-y-6">
          <RoleGroup title="专用角色" hint="参考音频读取自 samples/<角色名>/" roles={shown.filter((r) => !r.anonymous)} open={(r) => setDraft(toDraft(r))} />
          <RoleGroup title="匿名角色" hint="旁白、路人等，可使用任意音频" roles={shown.filter((r) => r.anonymous)} open={(r) => setDraft(toDraft(r))} />
        </div>
      ) : (
        <Empty icon={<Users size={18} />} title={q ? "没有匹配的角色" : "还没有角色"}>
          {!q && "新建与 samples 下文件夹同名的角色，文件夹中的音频即为其参考音频"}
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

function RoleGroup({ title, hint, roles, open }: { title: string; hint: string; roles: Role[]; open: (r: Role) => void }) {
  if (!roles.length) return null;
  return (
    <section>
      <h2 className="mb-2 flex items-baseline gap-2">
        <span className="text-[13px] font-semibold">{title}</span>
        <span className="text-xs text-muted">
          {roles.length} · {hint}
        </span>
      </h2>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-3">
        {roles.map((r) => (
          <div key={r.id} role="button" tabIndex={0} onClick={() => open(r)} onKeyDown={(e) => e.key === "Enter" && open(r)} className="card flex cursor-pointer flex-col gap-2.5 p-3 text-left transition-colors hover:border-accent/40 hover:bg-panel">
            <div className="flex items-center gap-2.5">
              <Avatar name={r.name} className={cx(r.anonymous && "bg-hover text-muted")} />
              <div className="min-w-0">
                <p className="truncate font-medium">{r.name}</p>
                <p className="text-xs text-muted">{r.anonymous ? "任意音频" : `${r.audio_ids.length} 段参考音频`}</p>
              </div>
            </div>
            <div className="flex min-h-5 flex-wrap gap-1">
              {r.tags.length ? r.tags.map((t) => <span key={t} className="chip">{t}</span>) : <span className="text-xs text-muted/60">无标签</span>}
            </div>
            {r.audio_ids.length > 0 && (
              <div onClick={(e) => e.stopPropagation()}>
                <Player id={r.audio_ids[0]} download={false} />
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function RoleEditor({ draft: initial, names, onClose, onSaved }: { draft: Draft; names: Map<string, string>; onClose: () => void; onSaved: () => void }) {
  const run = useAction();
  const [draft, setDraft] = useState(initial);

  async function save() {
    const body = { name: draft.name, tags: draft.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean), anonymous: draft.anonymous };
    const ok = await run(() => (draft.id ? api.put(`/roles/${draft.id}`, body) : api.post("/roles", body)), "角色已保存");
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
          <label
            className="tip tip-wide flex h-8 shrink-0 cursor-pointer items-center gap-1.5 text-[13px]"
            data-tip="旁白、路人等不固定声音的角色。勾选后在说话人绑定中可使用任意音频（同名文件夹中的音频优先列出）；不勾选则只能使用 samples/<角色名>/ 中的音频。"
          >
            <input type="checkbox" className="accent-[var(--accent)]" checked={draft.anonymous} onChange={(e) => setDraft({ ...draft, anonymous: e.target.checked })} />
            匿名角色
          </label>
        </div>
        <Field label="标签（逗号分隔）">
          <input className="input" placeholder="少女, 温柔" value={draft.tags} onChange={(e) => setDraft({ ...draft, tags: e.target.value })} />
        </Field>
        <FolderAudio draft={draft} names={names} />
      </div>
    </Sheet>
  );
}

/* Audio found in samples/<name>/: read-only here, managed in the file system. */
function FolderAudio({ draft, names }: { draft: Draft; names: Map<string, string> }) {
  const current = draft.id ? draft.saved : draft.name.trim();
  const next = draft.name.trim();
  const prefix = current + "/";
  return (
    <div>
      <span className="label flex items-center gap-1.5">
        <Folder size={12} />
        <span className="font-mono">samples/{current || "<名称>"}/</span>
        <span>· {draft.audio_ids.length}</span>
      </span>
      {draft.id && next && next !== current && <p className="mb-1.5 text-xs text-warn">改名后读取 samples/{next}/。已绑定的音频须在新文件夹中有同名文件（先在文件系统中重命名文件夹），否则无法保存。</p>}
      {draft.audio_ids.length ? (
        <div className="divide-y divide-line rounded-lg border border-line">
          {draft.audio_ids.map((id) => {
            const name = names.get(id) || id;
            return (
              <div key={id} className="flex items-center gap-2 px-2 py-1.5">
                <PlayButton id={id} />
                <span className="min-w-0 flex-1 truncate text-xs" title={name}>
                  {name.startsWith(prefix) ? name.slice(prefix.length) : name}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-xs leading-relaxed text-muted">把音频放进此文件夹（可含子文件夹）即成为参考音频；增删、改名直接在文件系统中进行。{!draft.id && "保存后读取。"}</p>
      )}
    </div>
  );
}
