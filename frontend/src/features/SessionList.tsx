import { useEffect, useState } from "react";
import { api, defaults, type Named, type Session } from "../api";
import { Cleanup } from "../components";

export function SessionList({
  project,
  projects,
  open,
  refreshProjects,
}: {
  project: Named | null;
  projects: Named[];
  open: (id: string) => void;
  refreshProjects: () => void;
}) {
  const [items, setItems] = useState<Session[]>([]),
    [sort, setSort] = useState("updated_at"),
    [error, setError] = useState("");
  const refresh = () =>
    api<Session[]>(
      `/sessions?sort=${sort}${project ? "&project_id=" + project.id : ""}`,
    )
      .then(setItems)
      .catch((e) => setError(e.message));
  useEffect(() => {
    void refresh();
  }, [project?.id, sort]);
  async function create() {
    try {
      let p = project || projects[0];
      if (!p) {
        const name = prompt("项目名称", "我的有声书");
        if (!name) return;
        p = await api<Named>("/projects", "POST", { name });
        refreshProjects();
      }
      const name = prompt("Session 名称", "新章节");
      if (!name) return;
      const s = await api<Session>("/sessions", "POST", {
        name,
        project_id: p.id,
        bindings: [],
        generation: defaults,
        interval: 0.5,
      });
      open(s.id);
    } catch (e) {
      setError(String(e));
    }
  }
  return (
    <section className="page">
      <header>
        <p className="eyebrow">多人对话 / 有声书</p>
        <h1>{project?.name || "最近的 Sessions"}</h1>
        <p className="muted">每句话，保留每一次声音的选择。</p>
      </header>
      <div className="toolbar">
        <button className="primary" onClick={() => void create()}>
          ＋ 新建 Session
        </button>
        <select
          aria-label="排序"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          <option value="updated_at">最近编辑</option>
          <option value="created_at">最近创建</option>
          <option value="name">名称排序</option>
        </select>
        {project && (
          <>
            <Cleanup
              path={"/projects/" + project.id}
              onDone={() => void refresh()}
            />
            <button
              onClick={async () => {
                const name = prompt("项目名称", project.name);
                if (name)
                  try {
                    await api("/projects/" + project.id, "PUT", { name });
                    refreshProjects();
                  } catch (e) {
                    setError(String(e));
                  }
              }}
            >
              重命名项目
            </button>
            <button
              className="danger"
              onClick={async () => {
                if (!confirm("删除项目及全部 session 和音频？")) return;
                try {
                  await api("/projects/" + project.id, "DELETE");
                  refreshProjects();
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              删除项目
            </button>
          </>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      <div className="session-list">
        {items.map((s) => (
          <div className="session-row" key={s.id}>
            <button className="session-open" onClick={() => open(s.id)}>
              <span className="session-icon">▤</span>
              <span>
                <strong>{s.name}</strong>
                <small>
                  {projects.find((p) => p.id === s.project_id)?.name} ·{" "}
                  {s.line_count} 句
                </small>
              </span>
            </button>
            <span className="muted">
              {new Date(s.updated_at).toLocaleDateString()}
            </span>
            <button
              className="danger"
              aria-label={"删除 " + s.name}
              onClick={async () => {
                if (!confirm("删除此 session 及全部音频？")) return;
                try {
                  await api("/sessions/" + s.id, "DELETE");
                  await refresh();
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              删除
            </button>
          </div>
        ))}
        {!items.length && (
          <div className="empty">
            <h2>从一个 Session 开始</h2>
            <p>创建章节，绑定角色，再添加你的文本。</p>
          </div>
        )}
      </div>
    </section>
  );
}
