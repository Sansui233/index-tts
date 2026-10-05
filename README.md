# IndexTTS WebUI

<img src="assets/index_icon.png" width="160"/>

基于 [IndexTTS 1.5](https://github.com/index-tts/index-tts)（[论文](https://arxiv.org/abs/2502.05512)）的本地 WebUI：React + Tailwind 前端，FastAPI 后端，直接调用仓库内 `indextts` 推理，无 Gradio 依赖。支持单句生成、字幕生成、角色管理、多人对话与有声书项目。模型许可见 `INDEX_MODEL_LICENSE`，使用须知见 `DISCLAIMER`。

## 目录

```text
backend/       FastAPI 服务
  routes.py      HTTP 层，只做请求转换
  storage.py     原子 JSON 记录    tasks.py   单 worker 任务队列
  engine.py      IndexTTS / Whisper 推理    audio.py   音频资源索引
  library.py     角色与多人预设    sessions.py 项目、session、句子与 Take
  generation.py  提交到 worker 的生成、字幕、合并任务
frontend/      React + Tailwind 前端（pnpm），构建产物 frontend/dist 由后端直接提供
  src/state.tsx  hash 路由、任务轮询、主题、toast    src/ui.tsx  基础组件与对话框
  src/player.tsx 共享音频播放器    src/widgets.tsx 参考音频、推理参数、说话人绑定
  src/pages/     各页面
indextts/      IndexTTS 1.5 推理代码
checkpoints/   模型权重与 config.yaml；Whisper 模型放在 checkpoints/whisper/whisper-{size}
samples/       参考音频（可为指向其他目录的链接）
data/          WebUI 数据：角色、预设、项目、session、Take 音频、任务（可用 WEBUI3_DATA 覆盖）
outputs/       旧版 webui2 输出，仅供 scripts/migrate_outputs.py 一次性迁移读取
scripts/       迁移与验证脚本
tests/         后端单元测试（fake engine）
```

`checkpoints` 权重、`samples`、`outputs`、`data` 均为用户数据，已在 `.gitignore` 中忽略。

## 安装与启动

环境：Python 3.12（uv 管理）、CUDA 12.8 版 PyTorch 2.8.0、pnpm、PATH 中的 `ffmpeg`（字幕与合并使用）。以下命令在仓库根目录执行。

```powershell
uv sync                                      # 创建 .venv；uv 缓存与项目同盘时以硬链接安装
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
uv run main.py                               # 或双击 run.bat；参数 --host / --port
```

打开 http://127.0.0.1:7863 ，API 文档为 http://127.0.0.1:7863/docs 。只使用单个 worker，以免重复加载 GPU 模型或并发写入 JSON。

依赖说明：
- 文本归一化使用 `wetext`（基于 kaldifst，自带 FST），替代 Windows 上难以安装的 WeTextProcessing/pynini。
- DeepSpeed 为可选：`uv sync --extra deepspeed`。未安装时推理回退到标准 PyTorch。
- `tokenizers` 使用 0.15.x 最新版（0.15.0 无 Python 3.12 wheel），满足 transformers 4.36.2 要求。

前端开发：保持 backend 运行，另开终端执行 `pnpm --dir frontend dev`，访问 http://127.0.0.1:5173 。Vite 将 `/api` 转发到 7863。修改 backend 后重启服务；任务队列不会跨进程继续执行。

## 使用

- 语音生成：选择上传音频或导入 samples 参考音频，输入文本，生成。任务面板显示进度、失败原因和下载链接。
- 字幕生成：上传/选择音频，选择本地 Whisper 模型和语言，下载 SRT。模型需位于 `checkpoints/whisper/whisper-{size}`。
- 角色管理：保存名称、标签、参考音频集合。多人预设在 session 设置中读取、保存或按同名更新。
- 项目管理：二级 Sidebar 切换项目；创建 session，在设置中配置角色绑定。空 session 支持批量解析 `[角色名] 文本`；非空 session 逐句修改，保留 index 与 Take。
- 句子 index 从 0 开始，代表稳定身份序号；排序通过有序句子列表维护，移动或删除句子不改变已有 index。新增句子的 index 不复用。
- 每次生成追加一个 Take；成功后默认设为当前。任务期间修改文本或手动选择当前 Take，新结果仍会保存，但不覆盖用户选择。Take 使用提交时的文本、参考音频及参数快照。
- 可以展开历史 Takes 试听，并设为当前。合并使用当前排列顺序和每句的当前 Take。
- 单句、session、项目均可清理非当前 Takes；清理会删除这些 Take 文件。当前 Take、其他引用以及活动任务使用的资源受保护。失败项保留供重试，Take 编号不回退。
- 设置可加载、卸载模型；推理自动加载。TTS 与 Whisper 串行使用 GPU，字幕运行前释放 TTS。取消在安全边界生效，不强制打断 CUDA 调用。

## 数据结构

```text
data/
  projects/<project_id>.json
  projects/<project_id>/sessions/<session_id>/
    index.json                  # session 索引镜像
    takes/<line_id>/<take_index>_<take_id>.wav
    merged/<id>.wav
  sessions/<session_id>.json    # API 使用的权威 session 索引
  roles/<id>.json
  presets/<id>.json
  audio/<id>.json               # 资源索引
  audio/files/                 # 上传、导入的参考音频
  outputs/                     # 独立语音、字幕输出
  tasks/<id>.json
  migrations/outputs.json       # 迁移映射和报告
  migrations/source-outputs/   # 原 JSON 快照
```

Session 中每句包含 `id/index/text/speaker/takes/current_take_id/next_take_index`。Take 包含 `id/take_index/audio_id/created_at/snapshot`。修改句子后仍保留旧 Take；输入快照用于判断内容是否过期。JSON 记录采用原子替换，进程内锁协调修改。

## 一次性迁移

```powershell
uv run python -m scripts.migrate_outputs
```

服务停止时执行。扫描旧 outputs 的 session JSON，复制关联音频，并把旧预设转为角色绑定。源文件不移动、不删除。源到目标映射保存在 `data/migrations/outputs.json`；重复运行跳过已经迁移的数据，保留 UI 修改。

旧索引每条记录转换为一条句子，其已有音频为 Take 1 并设为当前。项目名、时间、角色等缺失字段自动补全；默认参考音频会标记“待核验”。无确定归属的 session 放入“迁移项目”，可通过 session 设置修改所属项目。

## Take API

```text
POST /api/sessions/{session_id}/lines/{line_id}/generate
GET  /api/sessions/{session_id}/lines/{line_id}/takes
PUT  /api/sessions/{session_id}/lines/{line_id}/current-take
     {"take_id":"..."}
POST /api/sessions/{session_id}/lines/{line_id}/takes/cleanup
POST /api/sessions/{session_id}/takes/cleanup
POST /api/projects/{project_id}/takes/cleanup
```

清理返回 `deleted/bytes/failures`；生成或合并任务占用对应 session 时返回 HTTP 409。角色音频的增删通过角色 `audio_ids` 更新，重命名通过 `PATCH /api/audio/{id}`；解除关联不会删除源文件。

## 验证

```powershell
uv run python -m unittest discover -s tests -v
pnpm --dir frontend build
```

测试采用 fake engine，验证 Take 和任务状态，不代表真实 GPU 推理；实际验证记录见 `docs/verification.md`。
