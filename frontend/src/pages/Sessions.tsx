import type { MouseEvent } from "react";
import { Folder, Layers, Plus, Scissors, Trash2 } from "react-feather";
import { api, defaultGeneration, type Cleanup, type Named, type Preset, type Session } from "../api";
import { go, useAction, useApp, useLoad, useStored } from "../state";
import { ago, ask, choose, confirm, Empty, NameInput, Page, PageHeader, Segmented, type Choice, type DialogField } from "../ui";

type Sort = "updated_at" | "created_at" | "name";
export const CLEANUP_CHOICES: Choice[] = [
  { value: "all", label: "清理未使用的 Take 与已删除句子的音频", hint: "每句只保留当前 Take；台本中已删除句子的音频一并删除" },
  { value: "orphans", label: "仅清理已删除句子的音频", hint: "现有句子的 Take 都保留" },
];
export const cleanupMessage = (r: Cleanup) =>
  `已清理 ${r.deleted} 个 Take，释放 ${(r.bytes / 1048576).toFixed(1)} MB${r.failures.length ? `，${r.failures.length} 项失败` : ""}`;

export function Sessions({ project, projects, reloadProjects }: { project?: Named; projects: Named[]; reloadProjects: () => void }) {
  const run = useAction();
  const { notify } = useApp();
  const [view, setView] = useStored<{ sort: Sort }>("session-sort", { sort: "updated_at" });
  const query = `/sessions?sort=${view.sort}${project ? `&project_id=${project.id}` : ""}`;
  const sessions = useLoad<Session[]>(query, []);
  const projectName = new Map(projects.map((p) => [p.id, p.name]));
  const open = (s: Session) => go(project ? `projects/${project.id}/sessions/${s.id}` : `sessions/${s.id}`);

  async function create() {
    const fields: DialogField[] = [{ key: "name", label: "Session 名称", value: "新章节" }];
    if (!project)
      fields.push(
        projects.length
          ? { key: "project_id", label: "所属项目", options: projects.map((p) => ({ value: p.id, label: p.name })) }
          : { key: "project", label: "新项目名称", value: "我的有声书" },
      );
    const presets = (await run(() => api.get<Preset[]>("/presets"))) || [];
    if (presets.length)
      fields.push({ key: "preset_id", label: "多人预设", options: [{ value: "", label: "不使用预设" }, ...presets.map((p) => ({ value: p.id, label: p.name }))] });
    const values = await ask("新建 Session", fields, "创建");
    if (!values) return;
    const preset = presets.find((p) => p.id === values.preset_id);
    const session = await run(async () => {
      let projectId = project?.id || values.project_id;
      if (!projectId) {
        projectId = (await api.post<Named>("/projects", { name: values.project })).id;
        reloadProjects();
      }
      return api.post<Session>("/sessions", {
        name: values.name,
        project_id: projectId,
        bindings: preset?.bindings || [],
        generation: preset?.generation || defaultGeneration,
        interval: 0.5,
      });
    });
    if (session) open(session);
  }
  async function remove(e: MouseEvent, s: Session) {
    if (!(await confirm(e, `删除「${s.name}」及其全部生成音频？`))) return;
    if (await run(() => api.del(`/sessions/${s.id}`), "已删除")) void sessions.reload();
  }
  async function rename(name: string) {
    const ok = await run(() => api.put(`/projects/${project!.id}`, { name }));
    if (ok) reloadProjects();
    return !!ok;
  }
  async function cleanup(e: MouseEvent) {
    const mode = await choose(e, "清理此项目所有 session 的音频", CLEANUP_CHOICES);
    if (!mode) return;
    const result = await run(() => api.post<Cleanup>(`/projects/${project!.id}/takes/cleanup?mode=${mode}`));
    if (!result) return;
    notify(cleanupMessage(result), result.failures.length > 0);
    void sessions.reload();
  }
  async function removeProject(e: MouseEvent) {
    if (!(await confirm(e, `删除项目「${project!.name}」及其全部 Session 和音频？不可恢复。`))) return;
    if (await run(() => api.del(`/projects/${project!.id}`), "项目已删除")) {
      reloadProjects();
      go("projects");
    }
  }

  return (
    <Page>
      <PageHeader title={project ? <NameInput className="max-w-[40rem]" label="项目名称" value={project.name} onSave={rename} /> : "最近的 Session"} sub={project ? `${sessions.data.length} 个 Session` : "所有项目中的多人对话与有声书章节"}>
        {project && (
          <div className="flex">
            <button className="tip btn btn-ghost btn-icon" data-tip="清理未使用的 Take" aria-label="清理未使用的 Take" onClick={(e) => void cleanup(e)}>
              <Scissors size={14} />
            </button>
            <button className="tip btn btn-ghost btn-icon btn-danger" data-tip="删除项目" aria-label="删除项目" onClick={(e) => void removeProject(e)}>
              <Trash2 size={14} />
            </button>
          </div>
        )}
        <Segmented
          value={view.sort}
          onChange={(sort) => setView({ sort })}
          options={[
            { value: "updated_at", label: "最近编辑" },
            { value: "created_at", label: "创建时间" },
            { value: "name", label: "名称" },
          ]}
        />
        <button className="btn btn-primary" onClick={() => void create()}>
          <Plus size={14} />
          新建 Session
        </button>
      </PageHeader>
      {sessions.data.length ? (
        <div className="card overflow-hidden">
          <div className="grid grid-cols-[minmax(0,1fr)_72px_100px_36px] gap-3 border-b border-line bg-panel px-4 py-2 text-[11px] font-medium text-muted md:grid-cols-[minmax(0,1fr)_160px_72px_100px_36px]">
            <span>名称</span>
            <span className="hidden md:block">项目</span>
            <span className="text-right">句子</span>
            <span className="text-right">{view.sort === "created_at" ? "创建" : "编辑"}</span>
          </div>
          {sessions.data.map((s) => (
            <div
              key={s.id}
              role="button"
              tabIndex={0}
              onClick={() => open(s)}
              onKeyDown={(e) => e.key === "Enter" && open(s)}
              className="group grid cursor-pointer grid-cols-[minmax(0,1fr)_72px_100px_36px] items-center gap-3 border-b border-line px-4 py-2 last:border-0 hover:bg-panel md:grid-cols-[minmax(0,1fr)_160px_72px_100px_36px]"
            >
              <span className="flex min-w-0 items-center gap-2.5">
                <Layers size={14} className="shrink-0 text-accent" />
                <span className="truncate font-medium">{s.name}</span>
                <span className="hidden text-xs text-muted lg:inline">{s.bindings.length} 位说话人</span>
              </span>
              <span className="hidden truncate text-muted md:block">{projectName.get(s.project_id)}</span>
              <span className="text-right text-muted tabular-nums">{s.line_count}</span>
              <span className="text-right text-xs text-muted">{ago(view.sort === "created_at" ? s.created_at : s.updated_at)}</span>
              <button
                className="btn btn-ghost btn-sm btn-icon btn-danger opacity-0 group-hover:opacity-100"
                title="删除"
                onClick={(e) => {
                  e.stopPropagation();
                  void remove(e, s);
                }}
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        !sessions.loading && (
          <Empty icon={<Layers size={18} />} title="还没有 Session">
            新建一个章节，绑定说话人，再粘贴 [角色] 文本
          </Empty>
        )
      )}
    </Page>
  );
}

export function Projects({ projects, reload }: { projects: Named[]; reload: () => void }) {
  const run = useAction();
  const sessions = useLoad<Session[]>("/sessions", []);
  const stats = (id: string) => {
    const own = sessions.data.filter((s) => s.project_id === id);
    return { count: own.length, lines: own.reduce((n, s) => n + (s.line_count || 0), 0) };
  };
  async function create() {
    const values = await ask("新建项目", [{ key: "name", label: "项目名称" }], "创建");
    const p = values && (await run(() => api.post<Named>("/projects", values)));
    if (p) {
      reload();
      go(`projects/${p.id}`);
    }
  }
  return (
    <Page>
      <PageHeader title="项目" sub="有声书项目，每个项目包含多个 Session">
        <button className="btn btn-primary" onClick={() => void create()}>
          <Plus size={14} />
          新建项目
        </button>
      </PageHeader>
      {projects.length ? (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-3">
          {projects.map((p) => {
            const s = stats(p.id);
            return (
              <button key={p.id} onClick={() => go(`projects/${p.id}`)} className="card flex cursor-pointer items-start gap-3 p-3.5 text-left transition-colors hover:border-accent/40 hover:bg-panel">
                <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent">
                  <Folder size={16} />
                </span>
                <span className="min-w-0">
                  <span className="block truncate font-medium">{p.name}</span>
                  <span className="text-xs text-muted">
                    {s.count} 个 Session · {s.lines} 句 · {ago(p.updated_at)}
                  </span>
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <Empty icon={<Folder size={18} />} title="还没有项目" />
      )}
    </Page>
  );
}
