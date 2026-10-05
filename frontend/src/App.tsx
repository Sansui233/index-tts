import { useEffect, useState } from "react";
import {
  Mic,
  FileText,
  Users,
  Folder,
  Settings,
  Sun,
  Moon,
  Monitor,
  ArrowLeft,
  Activity,
} from "react-feather";
import { api, fileUrl, type Named, type Task } from "./api";
import { Player } from "./components";
import { Speech } from "./features/Speech";
import { Roles } from "./features/Roles";
import { SessionList } from "./features/SessionList";
import { SessionEditor } from "./features/SessionEditor";

export default function App() {
  const [view, setView] = useState("speech"),
    [projectMenu, setProjectMenu] = useState(false),
    [projects, setProjects] = useState<Named[]>([]),
    [projectId, setProjectId] = useState<string | null>(null),
    [sessionId, setSessionId] = useState<string | null>(null),
    [theme, setTheme] = useState(
      localStorage.getItem("webui3-theme") || "system",
    ),
    [tasks, setTasks] = useState<Task[]>([]),
    [model, setModel] = useState("unloaded"),
    [error, setError] = useState(""),
    [taskPanel, setTaskPanel] = useState(false);
  const project = projects.find((p) => p.id === projectId) || null;
  const refreshProjects = () =>
    api<Named[]>("/projects")
      .then(setProjects)
      .catch((e) => setError(e.message));
  useEffect(() => {
    void refreshProjects();
  }, []);
  useEffect(() => {
    const media = matchMedia("(prefers-color-scheme: dark)");
    const apply = () =>
      (document.documentElement.dataset.theme =
        theme === "system" ? (media.matches ? "dark" : "light") : theme);
    apply();
    localStorage.setItem("webui3-theme", theme);
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const c = new AbortController();
    async function poll() {
      let delay = 5000;
      try {
        const [t, m] = await Promise.all([
          api<Task[]>("/tasks", "GET", undefined, c.signal),
          api<{ state: string }>("/models", "GET", undefined, c.signal),
        ]);
        if (live) {
          setTasks(t);
          setModel(m.state);
          if (t.some((t) => ["queued", "running"].includes(t.status)))
            delay = 1000;
          setError("");
        }
      } catch (e) {
        if (live) setError(String(e));
      }
      if (live) timer = setTimeout(poll, delay);
    }
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
      c.abort();
    };
  }, []);
  const onTask = (task: Task) => {
    setTasks((t) => [task, ...t.filter((x) => x.id !== task.id)]);
    setTaskPanel(true);
  };
  const taskVersion = tasks
    .filter((t) => t.session_ids?.includes(sessionId || ""))
    .map((t) => t.id + t.status)
    .join(",");
  const navigate = (page: string) => {
    setView(page);
    setSessionId(null);
  };
  const active = tasks.filter((t) => ["running", "queued"].includes(t.status));
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">
            <Activity size={22} />
          </span>
          <div>
            IndexTTS<small>声音工作台</small>
          </div>
          <span className="version">3</span>
        </div>
        <nav>
          {projectMenu ? (
            <>
              <button onClick={() => setProjectMenu(false)}>
                <ArrowLeft size={17} />
                返回主菜单
              </button>
              <p className="nav-label">项目</p>
              {projects.map((p) => (
                <button
                  key={p.id}
                  className={
                    projectId === p.id && view === "sessions" ? "active" : ""
                  }
                  onClick={() => {
                    setProjectId(p.id);
                    navigate("sessions");
                  }}
                >
                  <Folder size={17} />
                  {p.name}
                </button>
              ))}
              <button
                onClick={async () => {
                  const name = prompt("项目名称");
                  if (name)
                    try {
                      const p = await api<Named>("/projects", "POST", { name });
                      await refreshProjects();
                      setProjectId(p.id);
                      navigate("sessions");
                    } catch (e) {
                      setError(String(e));
                    }
                }}
              >
                ＋ 新建项目
              </button>
            </>
          ) : (
            <>
              <p className="nav-label">创作</p>
              <button
                className={view === "speech" ? "active" : ""}
                onClick={() => navigate("speech")}
              >
                <Mic size={18} />
                语音生成
              </button>
              <button
                className={view === "subtitles" ? "active" : ""}
                onClick={() => navigate("subtitles")}
              >
                <FileText size={18} />
                字幕生成
              </button>
              <button
                className={view === "sessions" ? "active" : ""}
                onClick={() => {
                  setProjectId(null);
                  navigate("sessions");
                }}
              >
                <Users size={18} />
                多人对话生成
              </button>
              <div className="subnav">
                <button
                  className={view === "roles" ? "active" : ""}
                  onClick={() => navigate("roles")}
                >
                  角色管理
                </button>
                <button
                  onClick={() => {
                    setProjectMenu(true);
                    setProjectId(null);
                    navigate("sessions");
                  }}
                >
                  项目管理
                </button>
              </div>
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="model-state">
            <span className={model === "loaded" ? "dot loaded" : "dot"} />
            <span>
              模型 ·{" "}
              {(
                {
                  loaded: "已加载",
                  loading: "加载中",
                  unloaded: "未加载",
                  unloading: "卸载中",
                  error: "加载失败",
                } as Record<string, string>
              )[model] || model}
            </span>
          </div>
          <div className="row between">
            <button
              aria-label="设置"
              className={view === "settings" ? "active" : ""}
              onClick={() => navigate("settings")}
            >
              <Settings size={18} />
            </button>
            <div className="row theme">
              {[
                { id: "light", Icon: Sun, label: "日间" },
                { id: "dark", Icon: Moon, label: "夜间" },
                { id: "system", Icon: Monitor, label: "跟随系统" },
              ].map(({ id, Icon, label }) => (
                <button
                  key={id}
                  title={label}
                  aria-label={label}
                  className={theme === id ? "active" : ""}
                  onClick={() => setTheme(id)}
                >
                  <Icon size={16} />
                </button>
              ))}
            </div>
          </div>
        </div>
      </aside>
      <main>
        <div className="topbar">
          <span>本地工作区</span>
          <button onClick={() => setTaskPanel(!taskPanel)}>
            <Activity size={16} />
            任务{" "}
            {active.length > 0 && (
              <span className="badge">{active.length}</span>
            )}
          </button>
        </div>
        {error && <p className="error global-error">{error}</p>}
        {sessionId ? (
          <SessionEditor
            key={sessionId}
            id={sessionId}
            projects={projects}
            onBack={() => setSessionId(null)}
            onTask={onTask}
            taskVersion={taskVersion}
          />
        ) : view === "speech" ? (
          <Speech onTask={onTask} />
        ) : view === "subtitles" ? (
          <Speech key="subtitles" subtitle onTask={onTask} />
        ) : view === "roles" ? (
          <Roles />
        ) : view === "sessions" ? (
          <SessionList
            project={project}
            projects={projects}
            open={setSessionId}
            refreshProjects={() => void refreshProjects()}
          />
        ) : (
          <section className="page">
            <header>
              <p className="eyebrow">工作区</p>
              <h1>设置</h1>
            </header>
            <div className="card stack">
              <h2>模型与显存</h2>
              <p>生成任务会自动加载模型。卸载操作在当前推理完成后执行。</p>
              <div className="row">
                <button
                  onClick={() =>
                    api<Task>("/models/load", "POST")
                      .then(onTask)
                      .catch((e) => setError(e.message))
                  }
                >
                  加载 IndexTTS
                </button>
                <button
                  onClick={() =>
                    api<Task>("/models/unload", "POST")
                      .then(onTask)
                      .catch((e) => setError(e.message))
                  }
                >
                  卸载模型
                </button>
              </div>
              <p className="muted">
                数据目录：webui3/data
                <br />
                字幕仅使用 checkpoints/whisper 内的本地模型。
              </p>
            </div>
          </section>
        )}
      </main>
      {taskPanel && (
        <aside className="task-panel">
          <div className="row between">
            <h2>任务</h2>
            <button onClick={() => setTaskPanel(false)}>关闭</button>
          </div>
          {tasks.slice(0, 30).map((t) => (
            <div className="task" key={t.id}>
              <div className="row between">
                <strong>{t.kind}</strong>
                <span className="badge">{t.status}</span>
              </div>
              <progress max="1" value={t.progress} />
              <p className={t.error ? "error" : "muted"}>
                {t.error || t.message}
              </p>
              {["queued", "running"].includes(t.status) && (
                <button
                  onClick={() =>
                    api("/tasks/" + t.id + "/cancel", "POST").catch((e) =>
                      setError(e.message),
                    )
                  }
                >
                  取消
                </button>
              )}
              {t.result?.id &&
                (t.result.path.endsWith(".srt") ? (
                  <a href={fileUrl(t.result.id, true)}>下载 SRT 字幕</a>
                ) : (
                  <Player id={t.result.id} />
                ))}
            </div>
          ))}
          {!tasks.length && <p className="muted">暂无任务</p>}
        </aside>
      )}
    </div>
  );
}
