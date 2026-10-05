# WebUI3 实施计划

状态：实现完成，已通过 API、Take 测试、迁移校验和真实推理验证；浏览器交互/视觉检查因无可用浏览器连接未执行。2026-09-23。实际模块及启动方式见 ../README.md，验证记录见 verification.md。

## 目标与范围

完成 AGENTS.md 的 React + Python 前后端分离迁移，交付可运行的 API、界面、启动说明和必要测试。源码、前端依赖、文档和测试置于 webui3；所有新数据及运行输出统一置于 webui3/data。旧 outputs 保持原样，仅作为一次性迁移的数据源。保留 webui2 和 IndexTTS 推理实现。

这是跨模块架构变更，按下述边界实施，不把推理、存储和页面逻辑集中在一个文件。

## 已核实的现有实现

- indextts/infer.py：IndexTTS 初始化即加载模型；infer 与 infer_fast 接受参考音频、文本和输出路径；实例持有参考音频缓存；gr_progress 是可选回调，可接入普通 Python 回调。
- webui2/utils/tts_manager.py：Singleton 初始化时加载，无完整的并发控制及 unload 生命周期。新服务直接适配 IndexTTS，不沿用该 Singleton。
- webui2/ui/handlers/generate.py：生成、文本解析、拼接、字幕及 BGM 与 Gradio 交织，需要按职责迁移相关逻辑。
- 对话格式为每行 `[角色名] 文本`；空行和以半角/全角括号开头的注释行跳过。旧实现会静默跳过其他行；新编辑器应显示无效行，避免遗漏文本。
- outputs/temp_dialog/<session>/temp_list.json 为 [{text, audio_path}]，没有项目、角色绑定快照等信息。
- webui2/utils/preset_manager.py：旧 preset 含 speakers、settings、advanced_params；角色与音频通过 speakerN_name、speakerN_audio 保存。
- webui2/utils/subtitle_manager.py：使用本地 Whisper + transformers pipeline、FFmpeg、SRT 输出及模型清理。字幕应独立于 TTS 加载。
- 其他需保留的能力：服务器参考音频浏览、上传、普通/批次推理、高级参数、逐句重生成、句间隔、音频合并、字幕下载。按用户修订，不实现 BGM，包括 API、数据字段和 UI。
- 当前无 webui3 实现或既有计划；webui2/AI_NOTE.md 的部分目录描述已过时，以代码为准。

## 架构及目录

```text
webui3/
  backend/
    app.py              # API 组装与 lifespan
    config.py           # 路径、运行设置
    schemas/            # 请求、响应、持久化数据结构
    routers/            # models/tasks/audio/roles/presets/projects/sessions
    services/           # 模型、任务、生成、字幕、音频处理
    storage/            # 新格式 JSON 存储、文件访问
  scripts/              # 从旧 outputs 只读迁移到 data
  frontend/
    src/
      api/              # API client 与类型
      components/       # 布局、导航、播放器、状态反馈
      features/         # speech/subtitles/roles/projects/sessions/settings
      hooks/            # polling、主题等少量通用逻辑
    package.json
  tests/
  data/                 # WebUI3 独立数据根目录
    roles/              # 角色 JSON
    presets/            # 多人配置 JSON
    projects/           # 项目、session 索引镜像与关联生成结果
    sessions/           # 权威 session 索引（含文本、句子和 Take 引用）
    audio/              # 上传与迁移复制的参考音频、资源索引
    outputs/            # 独立单句生成、字幕等结果
    tasks/              # 任务记录
    temp/               # 运行临时文件
    migrations/         # 源 JSON 快照、迁移映射与报告
  docs/
  README.md
```

前端采用 React + TypeScript、Tailwind、Vite、pnpm；Feather 图标使用适配 React 的包或官方 SVG。音频第一版使用原生 audio 播放器，满足试听、进度、下载；暂不引入波形编辑库，当前无裁切或波形操作需求。

后端采用 FastAPI + 单进程服务 + 专用串行任务 worker。API 路由调用 service，service 调用 storage 或推理适配器。后台推理不阻塞 API event loop。禁止多 worker 各自加载模型。

不引入 Redis/Celery：当前为单机单 GPU、JSON 存储；专用 worker 足以提供串行执行。未来有多 GPU 或多进程需求时再替换任务执行层。

## 模型与任务

- 模型状态：unloaded/loading/loaded/unloading/error；单一管理实例管理引用和生命周期。
- 所有 load、unload 与推理经过相同串行执行边界；重复 load 幂等，推理前仅在未加载时加载。
- unload 在正在执行的推理之后处理，不在推理中释放模型。显式卸载时报告排队状态；后续用户提交的生成任务仍可按要求自动 load。
- 卸载清理模型、缓存与回调引用，再释放可回收显存；错误不得导致无限重试或重复初始化。
- Whisper 与 TTS 共用 GPU 调度边界；低显存默认按任务需要切换驻留模型，字幕不隐式加载 TTS。
- Task 包含 id、kind、status、progress、message、时间戳、结果引用及 error；状态包括 queued/running/succeeded/failed/cancelled/interrupted。
- 队列取消立即生效；运行中任务只在安全边界协作取消，不强制终止 CUDA 调用。
- 保存任务元数据；重启后未完成任务标记 interrupted，不自动重新执行昂贵推理。
- 前端活动任务约每秒 polling，空闲降低频率，页面卸载清理请求。选择 polling 是因为更新频率低、无需双向交互；暂不引入 WebSocket 连接管理。

## API 范围（统一 /api 前缀）

| 资源 | 行为 |
| --- | --- |
| health/settings | 健康检查、有效运行配置及可用参数 |
| models | 状态；POST load/unload，返回任务引用 |
| tasks | 列表、详情、取消；JSON 进度与错误 |
| speech | POST 单句任务，支持普通和批次推理及高级参数 |
| subtitles | POST 音频转字幕任务，模型与语言选择 |
| audio | 上传、服务器参考音频列表、预览、下载 |
| roles | 名称、标签 CRUD；角色参考音频增删改查 |
| dialogue-presets | list/read/save，保存角色名到指定参考音频的映射与生成配置 |
| projects | CRUD，项目下 session 列表及名称/创建时间/编辑时间排序 |
| sessions | CRUD、最近列表、角色绑定、原文、条目及生成结果 |
| session actions | 全文生成、单句重生成、按句间隔合并、可选字幕 |
| takes | 单句 Take 列表、切换当前 Take；单句/session/项目三级未使用 Take 清理 |

生成使用 POST 返回 202 与 task_id；GET 不触发生成。请求通过明确 schema 验证，错误返回统一 JSON。文件通过资源 ID 访问，限制可读取根目录，不开放任意系统路径。

## 数据及一次性迁移

- JSON 采用版本号、稳定 ID、created_at/updated_at；临时文件加原子替换，进程内锁避免并发写入丢失。
- Role：id/name/tags/audios；Audio：id/name/资源引用。允许引用已登记的 samples 音频，兼容当前 samples junction。
- DialoguePreset：id/name/bindings/settings；每个 binding 指定说话人名称及具体 role/audio。
- Project：id/name/时间戳。Session：id/project_id/name/角色绑定快照/原文/生成参数/条目/输出/时间戳。
- 每句具有稳定 ID、保留的 index、text、speaker、takes 和 current_take_id；index 用于句子定位和排序，删除其他句子不重编号，插入或排序显式更新顺序字段而不改变身份。Take 具有稳定 ID、句内递增 take_index、音频资源、生成输入快照和时间戳；清理后不复用 take_index。
- 单句重生成追加 Take，不覆盖旧音频。生成成功且文本/角色绑定及当前 Take 选择未被用户改动时，将新 Take 设为当前；失败保留原选择。编辑文本或参考音频后，历史 Take 保留，并根据快照显示是否匹配当前输入。
- 合并按句子顺序读取 current_take_id；缺少可播放的当前 Take 时返回具体句子 index。用户可试听历史 Take 并切换当前版本。
- 新 session 保存于 webui3/data/projects/<project_id>/sessions/<session_id>/；角色、配置、上传音频、任务、生成音频、字幕及临时文件均在 webui3/data 下分类存储。禁止向旧 outputs 写入新数据。
- 不实现旧 session 的运行时兼容、legacy API 或导入页面；应用仅操作新格式。交付前从旧 outputs 一次性迁移到 webui3/data，源目录不修改、不移动、不删除。
- 迁移脚本扫描 outputs 中的 session JSON（包括 temp_dialog 和其他章节目录），按数据结构识别，跳过无关 JSON、备份目录及新格式目录。已发现章节目录也有旧格式记录，不能仅扫描 temp_dialog。
- 在 webui3/data/migrations 保存原始 JSON 快照及源路径到新 ID 的映射；重复运行不重复创建，不覆盖迁移后在 UI 中编辑的数据。将关联生成音频及迁移采用的参考音频复制到新数据目录，重写新记录中的资源引用，使迁移后的 session 不依赖旧 outputs；原始音频保持不变。无关联的旧输出文件留在原处。
- 自动补全项目、session、角色、条目 ID 和时间戳：以目录/文件名推导名称，按章节所在目录分组；无法确定项目归属时放入“迁移项目”。原文从有序条目重建；时间优先使用源文件时间，并记录推导来源。
- 从文本中的角色名创建角色；优先匹配旧 preset 中同名角色的有效参考音频。仍无法确定时，从已登记的有效参考音频中选择稳定的默认值并标记待核验；无可用音频时保存空绑定并阻止对应生成，不伪造文件路径。标签默认空数组，生成参数采用统一默认值。
- 旧 audio_path 先校验存在性，再尝试 session 目录及唯一同名文件匹配；存在歧义或无法找到时保留原始引用并标记缺失，不悄悄绑定其他音频。重复索引基于内容和音频引用识别，保留不同版本。
- 迁移报告列出数量、合并的重复项、自动补全字段、默认绑定与缺失文件；已有生成音频保持可试听，不因为迁移而重生成。
- 迁移时保留旧句序 index，每个已有音频转为一个 Take 并设为当前；只有能确认属于同一条目的历史音频才归入其 Take 列表，不按相似文本误合并。
- UI 必须支持核验和修正补全结果：项目/session 重命名、session 项目归属、角色名称与标签、参考音频绑定、文本/条目及生成参数；保存并重新打开后保持修改。
- 删除角色/音频时检查引用；默认不删除外部源音频。项目和 session 删除限定在 WebUI3 管理的数据范围。

## 界面

- Notion 风格简洁布局，淡蓝主色；light/dark/system，保存用户选择并监听系统主题变化。
- 一级 Sidebar：语音生成、字幕生成、多人对话最近 session、角色管理、项目管理；底部设置与主题选择。
- 项目管理切换二级 Sidebar：返回、项目列表和新建操作。右侧 session 列表提供名称/编辑时间/创建时间排序。
- session 页面顶部固定返回按钮及项目/session 面包屑；支持角色与参考音频绑定、文本编辑、逐句试听、重生成、合并及下载。每句展示 index、Take 编号、当前标记、历史 Take 试听/切换；提供单句、session、项目级未使用 Take 清理。

## Take 清理规则

- 以持久化 session index（句子与 Take 引用记录）为依据，不靠文件名或最新修改时间推断当前 Take。
- POST /sessions/{session_id}/lines/{line_id}/takes/cleanup：清理指定句子的非当前 Take。
- POST /sessions/{session_id}/takes/cleanup：对该 session 所有句子执行相同规则。
- POST /projects/{project_id}/takes/cleanup：对该项目所有 session 执行相同规则。
- 清理保留 current_take_id 引用的 Take，且不处理正在生成或被活动任务使用的文件；有冲突时返回 busy，避免切换当前 Take 与清理竞争。
- 删除前在锁内重新读取索引，校验文件属于对应 WebUI3 session 的 Take 目录；不得删除旧 outputs、参考音频或其他句子的当前 Take。
- 返回清理范围、删除 Take 数、释放字节数及失败项；失败项保留索引以便重试，文件已缺失时可移除无效的非当前记录。Take 计数器不回退。
- 针对性测试覆盖重生成保留历史、手动切换、三级清理保留当前版本、index/Take 编号不复用、生成与清理冲突和删除失败。
- 单句页提供参考音频与文本、折叠高级参数、生成状态及结果。字幕页提供音频上传、模型/语言、任务状态及 SRT 下载。
- 全局可见模型状态与任务进度；实际接入所有按钮，覆盖空列表、加载及错误状态。设置提供模型 load/unload。

## 实施顺序与验收

1. 基础工程：确认运行环境；创建 API、frontend、配置和启动入口；验证健康检查及页面启动。
2. 后端数据管理：存储、音频、角色、预设、项目/session 和一次性迁移脚本；验证 CRUD、路径限制与迁移结果。应用只读取新格式。
3. 推理任务：串行 worker、模型生命周期、单句/批量/重生成、字幕、合并；验证状态流和异常恢复。
4. 前端：完成布局、主题、两级导航及全部功能页；与真实 API 联调。
5. 数据迁移与交付：从旧 outputs 只读迁移到 webui3/data，交付迁移报告，确认源数据未改变且新资源引用位于新数据目录；在 UI 中验证迁移数据的展示、试听、字段编辑和重新打开。完成后端针对性测试、前端类型检查和 production build、浏览器主要流程检查；在环境可用时执行真实短句推理、播放与 unload 验证。记录缺少的模型/依赖，不将 mock 测试当作真实推理通过。

重点测试：并发请求只加载一次、推理与 unload 互斥、失败后可执行下一个任务；JSON CRUD 与重启读取；一次性迁移的字段补全、重复运行和缺失音频处理；文本解析；逐句更新与过期输出；路径越界拒绝。使用 fake engine 验证调度以避免测试反复加载模型。

## 环境、约束与风险

- 使用 uv 运行 Python，pnpm 管理 frontend。先检查现有 .venv 与指定 conda 环境的依赖，再确定 WebUI3 的 project-level uv 环境；不直接改动已有根 pyproject.toml 或升级推理环境。
- 不主动安装或升级 torch；确有缺失时按用户指定 2.8.0/cu128 组合与 F 盘缓存配置处理。
- 推理依赖版本较旧，Web API 依赖须与已安装版本兼容；实施时记录实际验证版本。
- Whisper 权重、CUDA、FFmpeg 是否可用需运行时检查；缺少组件时相关任务明确失败，CRUD 和页面仍可使用。
- 当前工作区有用户修改，保留这些修改；实现产物限定 webui3，所有新数据和运行输出写入 webui3/data，旧 outputs 保持原样。
- GPU 单次调用不能可靠强行取消；UI 明确显示等待当前句完成。
- 本方案覆盖完整功能流程和基础框架，视觉细节按用户后续要求继续调整。

## 文档核对

已通过 ctx7 library 后执行 ctx7 docs 核对 FastAPI lifespan 和后台任务资料：
- https://fastapi.tiangolo.com/advanced/events
- https://fastapi.tiangolo.com/tutorial/background-tasks

串行 worker 是本项目针对 GPU 共享与任务可查询性的设计选择，并非直接用 BackgroundTasks 替代任务管理器。实现前通过 ctx7 核对 React、Tailwind、Vite 及实际采用依赖的配置文档。
