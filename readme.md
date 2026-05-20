# NanoMem

NanoMem 是一个面向智能体的长期个人记忆数据库。它只管理跨会话、用户相关、可长期保留的个人记忆，不替代项目文档、代码搜索、任务状态或工作区知识库。

现代 coding/local agent 已经可以直接读取文件、搜索仓库、查看日志、使用 git 和检查构建产物。NanoMem 的设计假设是：这些本地工具应该继续作为 workspace context 的 source of truth；NanoMem 只负责 local file storage 不擅长管理的长期个人记忆。

一句话定位：

```text
Agent can read the workspace. NanoMem helps it remember the user.
```

核心接口保持很小：

- `capture`：从用户可见事件中提取并写入个人事实记忆单元。
- `read`：按查询、时间范围和作用域读取相关记忆，并生成可放入上下文的摘要文本。

模块化设计规范见 [docs/nanomem/README.md](docs/nanomem/README.md)。系统设计总入口见 [docs/system-design.md](docs/system-design.md)。详细产品边界见 [docs/nanomem-product-rfc.md](docs/nanomem-product-rfc.md)，agent 场景下的读写准则见 [docs/agent-memory-positioning.md](docs/agent-memory-positioning.md)，插件适配方案见 [docs/plugins/README.md](docs/plugins/README.md)，架构总览见 [docs/architecture-overview.md](docs/architecture-overview.md)，索引后端策略见 [docs/index-backends.md](docs/index-backends.md)，代码架构见 [docs/nanomem-code-architecture.md](docs/nanomem-code-architecture.md)。

## 项目定位

NanoMem 不是 all-in-one memory layer。它不试图把文档、代码、日志、任务状态、对话历史和用户偏好全部放进同一个系统。那类宽记忆系统适合没有强本地工具、需要托管统一上下文的 agent；NanoMem 更适合已经具备本地读取能力的 agent。

边界如下：

| 信息类型 | 归属 |
| --- | --- |
| README、设计文档、ADR、代码、配置 | 本地文件 / repo |
| PDF、图片、音频、视频、截图、数据集 | 本地文件 / 对象存储 / 专用媒体库 |
| 当前任务计划、CI 日志、构建输出 | session / logs / artifacts |
| 项目测试命令、项目约定 | repo docs / `AGENTS.md` |
| 用户偏好、沟通风格 | NanoMem |
| 用户纠正过的 agent 行为 | NanoMem |
| 用户长期习惯、个人背景、关系事实 | NanoMem |
| 与用户长期相关的重要事件 | NanoMem |

这可以避免重复 source of truth，也避免项目文档、旧日志和用户偏好在同一个检索池里竞争上下文预算。

## 记忆单元

长期个人记忆不只包括静态偏好，也包括与用户长期相关的事件事实。NanoMem 存储的是细粒度 personal memory units，例如：

- 用户偏好：`用户更喜欢简洁的中文回答。`
- 行为纠正：`用户明确要求不要自动提交代码。`
- 长期习惯：`用户通常希望先讨论设计边界，再进入实现。`
- 个人事件：`用户决定 NanoMem 只做 long-term personal memory，不做通用 workspace memory。`
- agent 交互事件：`agent 曾自动提交代码，用户对此表达了负面反馈。`
- 背景或关系事实：`用户正在设计一个面向 agent 的长期记忆后端。`

不应写入 NanoMem 的内容包括：项目文件全文、代码片段、CI 日志、一次性任务计划、raw tool output、完整聊天归档、多模态资源原文件。需要审计时，可以保留不可检索的 `DialogueRecord`；正常记忆只通过 `DialogueRef` 指向用户可见对话。

“发生了什么”可以进入 NanoMem，但必须是长期个人相关的事件事实，而不是完整事件流。用户发生的重要事件、用户做出的长期决定、agent 做过且会影响未来协作方式的可见行为，都可以被抽取成 MemoryUnit；agent 的普通工具调用、内部步骤、临时任务进展和操作日志仍然留在 harness、workspace 或日志系统中。

多模态资源的处理方式也是同一原则：图片、音频、视频、PDF 或截图本身应保留在原始存储中；agent 或工具读取这些资源后，把对用户长期有用的信息体现在用户可见对话里。NanoMem 只从这段对话中抽取事实，例如“用户偏好用手绘草图讨论 UI 方向”，证据指向 `DialogueRecord`，而不是直接引用资源 URI、页码或片段。

## 算法思路

研究结论表明，在 long-term personal memory 场景下，细粒度 fact-form memory 比 raw chunk 更适合作为存储和检索单元。

NanoMem 的管线设计是：

```text
user-visible dialogue
  -> chunk = n for extraction
  -> role-aware / speaker-aware fact extraction
  -> store fine-grained MemoryUnits
  -> retrieve relevant facts
  -> render facts under a post-render token budget
```

`chunk = n` 是抽取阶段的窗口参数，不是存储模型。持久化对象仍然是 `MemoryUnit`。读取阶段检索 fact，而不是检索原始对话块；render 阶段在相同 post-render token budget 下尽量放入更多相关 fact。每条渲染记忆必须保留时间；其他展示字段如 dialogue ref、namespace、confidence、tags 或项目提示由宿主自定义。

## 当前状态

本仓库处于早期实现阶段，当前包含 Python 源码、HTTP 服务、MCP 服务、CLI 管理命令、SQLite 存储、词法/向量/混合索引、启发式与 LLM 记忆提取器。项目已提供 `pyproject.toml`、pytest 回归测试和 GitHub Actions CI；依赖锁文件仍未引入。

## 目录结构

```text
src/nanomem/
  contracts.py        # 核心数据契约：MemoryScope、CaptureRequest、ReadRequest 等
  config.py           # JSON / 简单 YAML 配置加载
  factory.py          # 根据配置组装 store、index、extractor、service
  service/            # capture/read 编排逻辑
  store/              # SQLite 持久化
  index/              # lexical、dense、hybrid 索引；向量库 adapter 可后续扩展
  embeddings/         # hashing 与 OpenAI-compatible embedding
  extraction/         # heuristic 与 LLM 提取器
  server/             # HTTP API
  mcp/                # MCP stdio 服务
  cli/                # 管理命令
  control/            # 统计、迁移、备份、导出、保留策略
  maintenance/        # 维护计划和自动化执行
  manager/            # 本地网页管理台静态资源
docs/                 # 产品与架构文档
tests/                # pytest 回归测试
.github/workflows/    # CI
```

## 快速开始

建议先在本地虚拟环境中安装开发依赖：

```bash
python -m pip install -e ".[dev]"
nanomem --help
nanomem-server --help
nanomem-mcp --help
```

创建一个最小配置文件 `nanomem.json`：

```json
{
  "data_dir": ".nanomem",
  "store": {
    "backend": "sqlite"
  },
  "index": {
    "backend": "dense"
  },
  "extraction": {
    "backend": "heuristic"
  },
  "read": {
    "default_recency_policy": "balanced",
    "default_max_units": 10
  }
}
```

默认本地状态会集中在 `data_dir` 下：

```text
.nanomem/
  nanomem.db      # SQLite fact store
  lancedb/        # future local ANN index
  backups/        # optional backups
  exports/        # optional exports
```

启动 HTTP 服务：

```bash
nanomem-server --config nanomem.json --host 127.0.0.1 --port 8765
```

健康检查：

```bash
curl http://127.0.0.1:8765/v1/health
```

本地网页管理台：

```text
http://127.0.0.1:8765/manager
```

该页面是 control-plane，用于观察 MemoryUnit、DialogueRecord、operation logs、
retrieval preview 和 index health；不要把这些 manager/control endpoints 暴露成 MCP
或 agent-facing tools。`/admin` 仍保留为兼容别名，JSON control-plane API 位于
`/manager/api/*`。

## Agent 插件接入

Codex 和 Claude Code 的 repo-local 插件骨架位于：

```text
.agents/plugins/marketplace.json
plugins/nanomem-codex/
plugins/nanomem-claude-code/
```

Codex 本地插件可通过仓库 marketplace 注册：

```bash
codex plugin marketplace add /path/to/nanomem
```

这是显式 opt-in 的宿主适配流程，不属于 NanoMem 默认系统安装。只有确认要让
Codex 自动读写 NanoMem 时，才在 Codex `/plugins` 中安装 `nanomem-codex`，
开启 `plugin_hooks`，并在 `/hooks` 中信任 NanoMem hooks。
详细安装、验证和原理说明见
[docs/plugins/codex-installation.md](docs/plugins/codex-installation.md)。

两者共用 hook runner：

```bash
nanomem-agent-hook read --host codex
nanomem-agent-hook capture --host codex
nanomem-agent-hook read --host claude-code
nanomem-agent-hook capture --host claude-code
```

插件默认通过 HTTP 连接本地 sidecar。先启动服务并设置环境变量：

```bash
nanomem-server --config .nanomem/config.json
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
```

如果不设置 `NANOMEM_NAMESPACE`，hook 会按默认策略读取所有 namespace，并以
无 namespace 的 scope 写入。

真实宿主联调时可以临时开启 hook payload 调试：

```bash
export NANOMEM_HOOK_DEBUG_DIR=.nanomem/hook-debug
```

该目录会保存 hook stdin JSON，便于确认 Codex / Claude Code 实际字段。正常使用时不要开启，避免长期保存用户 prompt 或 transcript metadata。

自动 capture 由 hook 直接调用 `/v1/capture`，不要走 MCP；MCP 只保留
`nanomem_read` 和显式的 `nanomem_capture`。

## HTTP API 示例

写入一条用户偏好：

```bash
curl -X POST http://127.0.0.1:8765/v1/capture \
  -H 'Content-Type: application/json' \
  -d '{
    "scope": {"owner_id": "demo-user", "namespace": "personal"},
    "dialogue": {
      "messages": [
        {
          "role": "user",
          "speaker_id": "user:demo-user",
          "content": "我更喜欢简洁的中文回答。",
          "timestamp": "2026-05-19T10:00:00+08:00"
        }
      ],
      "occurred_at": "2026-05-19T10:00:00+08:00",
      "metadata": {"host_log": "local-demo"}
    },
    "capture_time": "2026-05-19T10:00:05+08:00"
  }'
```

读取相关记忆：

```bash
curl -X POST http://127.0.0.1:8765/v1/read \
  -H 'Content-Type: application/json' \
  -d '{
    "owner_id": "demo-user",
    "namespaces": ["personal"],
    "query": "回答风格偏好",
    "query_time": "2026-05-19T10:01:00+08:00",
    "max_units": 5,
    "context_budget_tokens": 600
  }'
```

## CLI 管理

CLI 面向本地 SQLite 数据库管理和维护：

```bash
PYTHONPATH=src python -m nanomem.cli stats --config nanomem.json
PYTHONPATH=src python -m nanomem.cli list --config nanomem.json --limit 20
PYTHONPATH=src python -m nanomem.cli migrations --config nanomem.json
PYTHONPATH=src python -m nanomem.cli integrity-check --config nanomem.json
PYTHONPATH=src python -m nanomem.cli dashboard --config nanomem.json
```

备份和导出示例：

```bash
PYTHONPATH=src python -m nanomem.cli backup --config nanomem.json --output backup.db
PYTHONPATH=src python -m nanomem.cli export --config nanomem.json --output export.json
```

## MCP 服务

MCP 入口通过 stdio 运行，适合集成到支持 MCP 的宿主智能体：

```bash
PYTHONPATH=src python -m nanomem.mcp --config nanomem.json
```

MCP / agent-facing tools should expose normal `capture` and `read` only.
Backup, export, retention, delete, reindex, and DialogueRecord inspection belong
to CLI or another control-plane surface.

## 配置后端

当前工厂支持以下配置值：

- `store.backend`: `sqlite`
- `index.backend`: `lexical`、`dense`、`hybrid`
- `index.embedding.backend`: `hashing`、`openai_compatible`
- `extraction.backend`: `heuristic`、`llm`

使用 OpenAI-compatible embedding 或 LLM 提取器时，优先通过 `api_key_env` 指向环境变量，不要把密钥写入仓库文件。

SQLite 是当前默认和已实现的事实存储，默认路径是 `.nanomem/nanomem.db`，适合本地、单用户和 agent sidecar 场景。
默认检索后端是 `dense`，默认 embedding 是本地 deterministic hashing，因此可以离线启动。
配置化启动时默认 `index.rebuild_on_startup = true`，服务会从 SQLite 中已存的
MemoryUnit 重建当前内存索引，保证重启后仍能读取已有记忆。
当前 `dense` 是轻量本地索引：先按 owner/namespace scope 缩小候选，再按最近时间
顺序做有上限的 similarity scan，默认 `index.dense_scan_limit = 2000`。如果
以后需要低延迟 ANN 语义检索，不在 NanoMem 内部实现 ANN；应通过新的
`MemoryUnitIndex` adapter 接入数据库。优先考虑两条路线：LanceDB 作为本地
embedded vector index，或 Postgres + pgvector 作为事实存储和向量索引合一的
托管后端。不要把 SQLite 扩展成 JSON vector 扫描引擎。

## 开发说明

代码采用 Python `src/` 布局。新增模块应保持现有依赖方向：`server -> service -> store/index/extraction/ranking/render -> contracts`。核心契约放在 `contracts.py`，HTTP JSON 转换放在 `serde.py`/`server/schemas.py`，跨模块组装放在 `factory.py`。

建议新增测试时使用 `pytest`，并按源码路径组织，例如：

```text
tests/service/test_core.py
tests/store/test_sqlite.py
tests/server/test_app.py
```

运行测试的预期命令：

```bash
PYTHONPATH=src python -m pytest
```

## 安全与数据

NanoMem 存储的是个人记忆数据。不要提交本地数据库、导出的记忆 JSON、API key、`.env` 或包含真实用户内容的测试夹具。涉及删除、保留策略、备份和导出功能时，应优先使用临时路径和最小化样例数据。
