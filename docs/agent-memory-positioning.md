# Agent Memory Positioning

Status: draft

本文说明 NanoMem 在现代 agent harness 中的定位，以及不同类型 agent 应该如何获取和存储记忆。

## 1. 核心判断

NanoMem 不是 all-in-one memory layer，而是 long-term personal memory
database。

现代 agent harness，例如 Claude Code、Codex、OpenClaw 这类 coding/local
agent，已经把本地文件、仓库搜索、终端命令、日志、git 状态、项目指令和
MCP 工具作为主要上下文来源。NanoMem 不应该复制这些能力，也不应该把
workspace 内容重新托管成第二套记忆系统。

合理分工是：

```text
agent harness        = tool/runtime/context orchestrator
workspace/files      = artifact source of truth
NanoMem              = durable personal memory database
```

换句话说：

```text
The agent reads the workspace. NanoMem helps it remember the user.
```

## 2. 为什么要窄设计

把所有内容放进一个 memory 系统会带来几个问题。

第一，source of truth 重复。项目文档、代码、配置、多模态资源和日志已经
存在于文件系统、仓库、对象存储或专用工具中。NanoMem 再存一份会产生 stale
copy，agent 难以判断该相信当前文件还是历史记忆。

第二，检索池污染。workspace 内容体量大且变化快，容易淹没用户偏好、长期习
惯、纠正和个人事件。NanoMem 的价值在于让这些 personal memory units 在跨
项目、跨会话时仍然可检索。

第三，生命周期不同。CI 日志和任务计划可能数小时后过期，代码片段随 commit
变化，多模态文件有自己的存储和权限策略；用户偏好、沟通风格、长期习惯和重
要个人事件可能跨月有效。

第四，权限边界更清楚。agent harness 通常已经有 sandbox、approval、workspace
policy 和 tool policy。NanoMem 只保存细粒度个人事实，并通过 `DialogueRef`
指向用户可见对话证据，避免绕开 harness 原生权限模型。

第五，窄问题可以做深。NanoMem 可以专门优化 role-aware fact extraction、
time-aware retrieval、post-render token budget 下的 fact coverage、retention、
privacy delete 和 audit，而不是做一个什么都存一点的宽平台。

## 3. NanoMem 应该存什么

NanoMem 存储细粒度、长期有效、用户相关的 personal memory units。

应该存：

- 用户偏好：回答风格、语言、工作方式、工具选择偏好；
- 用户纠正：用户明确指出 agent 应该避免或改变的行为；
- 长期习惯：跨项目反复出现的工程、写作或沟通习惯；
- 个人背景：长期影响交互的角色、目标、约束和上下文；
- 关系事实：用户与人、组织、工具、agent 或项目的长期关系；
- 用户相关事件：会影响未来交互的重要决定、经历或状态变化；
- agent 交互事件：agent 做过且会影响未来协作方式的用户可见行为；
- 从多模态资源讨论中抽取出的长期个人事实，前提是相关信息已经出现在用户可见对话里。

不应该存：

- 项目文档、README、ADR、代码、配置全文；
- 当前任务计划、scratchpad、issue 临时状态；
- CI 日志、构建输出、raw tool output；
- 完整聊天归档、隐藏推理、tool calls、tool results、agent 普通操作轨迹；
- PDF、图片、音频、视频、截图、数据集等原始多模态资源；
- 可以由 agent 直接从 workspace 或外部系统读取的业务记录原文。

事件记忆不是 event sourcing。NanoMem 可以保存“用户发生了什么”“用户做了
什么长期决定”“agent 做过什么用户可见行为并改变了未来协作方式”，但这些都
应该被抽取成细粒度事实。完整操作日志、工具调用序列和当前任务进展仍然属于
harness、workspace 或日志系统。

## 4. 通用读写模式

所有 agent 集成都应遵循同一个生命周期。

Before turn:

```text
1. agent 从 workspace / tools 读取当前任务相关上下文
2. agent 用用户消息、当前目标和必要 scope 调用 NanoMem.read
3. agent 将 NanoMem 返回的 rendered personal facts 注入 prompt
```

After turn:

```text
1. agent 只把用户可见 dialogue 交给 NanoMem.capture
2. capture 按 role/speaker 和 chunk = n 抽取 personal facts
3. NanoMem 存储 MemoryUnits，并保留 `DialogueRef`
4. agent 不把隐藏推理、工具输出、日志或项目文件全文写入 NanoMem
```

NanoMem 的基本算法管线是：

```text
user-visible dialogue
  -> chunk = n for extraction
  -> role-aware / speaker-aware fact extraction
  -> store fine-grained MemoryUnits
  -> retrieve relevant facts
  -> render facts under a post-render token budget
```

## 5. 不同 Agent 场景

### 5.1 Coding / Local Agent

适用于 Claude Code、Codex、OpenClaw-like harness。

读取：

- 代码、README、测试命令、AGENTS.md、日志、git diff：用本地工具读取；
- 用户长期偏好、纠正、跨项目习惯：用 NanoMem.read；
- repo-specific 规则优先来自 workspace，NanoMem 只提供用户级背景。

写入：

- 用户说“以后不要自动提交代码”：写入 NanoMem；
- 用户说“这个 repo 用 pytest”：优先写入 repo docs 或 AGENTS.md；
- CI 失败日志、build output、tool output：不写入 NanoMem；
- agent 曾自动提交并引发用户负面反馈：写入 NanoMem 作为 agent 交互事件；
- agent 在当前任务中修改了哪些文件：保留在 git diff / workspace，不写入 NanoMem；
- 用户长期偏好某种开发流程：写入 NanoMem。

### 5.2 Personal Assistant / Chat Agent

读取：

- 当前对话短期上下文：来自 session；
- 用户长期偏好、背景、关系、重要事件：来自 NanoMem；
- 日历、邮件、外部系统记录：从对应工具读取，NanoMem 只保留长期个人事实。

写入：

- 用户稳定偏好、生活背景、长期计划或重要个人事件：写入 NanoMem；
- 临时提醒、一次性任务、完整邮件正文：放在任务系统或外部工具，不写入 NanoMem。

### 5.3 Research / Browser Agent

读取：

- 网页、论文、报告、引用：从浏览器、文件系统或文献库读取；
- 用户研究偏好、写作风格、长期项目方向：从 NanoMem 读取。

写入：

- 用户长期偏好某种文献综述结构：写入 NanoMem；
- 网页全文、PDF 全文、临时搜索结果：不写入 NanoMem；
- 用户做出的长期研究方向决定：可以写入 NanoMem，并通过 `DialogueRef` 引用对话证据。

### 5.4 Multimodal Agent

读取：

- 图片、音频、视频、PDF、截图原文：从文件系统、对象存储或媒体处理工具读取；
- 用户对视觉、语音、文档处理方式的长期偏好：从 NanoMem 读取。

写入：

- 资源原文件不写入 NanoMem；
- 从资源讨论中抽出的长期个人事实可以写入 NanoMem；
- 证据指向用户可见对话，不直接把 URI、页码、时间戳、bbox 或 segment id 作为 agent-facing memory evidence。

### 5.5 Enterprise / CRM Agent

读取：

- CRM 记录、工单、合同、知识库：从系统 of record 读取；
- 用户或客户经理的长期偏好、沟通习惯、关系事实：从 NanoMem 读取。

写入：

- 业务记录原文继续留在 CRM / ticket system；
- 可长期影响交互的个人事实写入 NanoMem；
- tenant、user、agent、project scope 必须清晰，避免跨客户泄露。

### 5.6 Multi-user / Multi-agent Conversation

读取：

- 对每个参与者使用独立 scope 读取个人记忆；
- 群组当前上下文来自 session，不直接混入某个用户的 personal memory。

写入：

- capture 必须按 speaker/role 抽取；
- 属于 Alice 的事实写入 Alice scope，属于 Bob 的事实写入 Bob scope；
- assistant final reply 可以作为 dialogue message 参与抽取，但隐藏推理和工具调用不能写入。

## 6. 实现准则

集成 NanoMem 时，agent harness 应该做到：

- 在 prompt 中明确区分 workspace context 和 personal memory context；
- personal memory 只作为证据，不作为覆盖 workspace 文件的最高优先级规则；
- first-version capture 不提供幂等去重，hook / wrapper 应避免重复提交已完成的 capture；
- 对 read 使用 time range、scope、context budget，避免无界检索；
- 默认只 capture 用户消息，assistant 只 capture 最终用户可见回复；
- 对多模态、外部系统和 workspace 资源不存原文，也不把资源引用暴露为普通 memory evidence；需要审计时只在控制面 `Dialogue.metadata` 保留宿主日志线索；
- 对删除、导出、保留策略和审计按用户级个人数据处理。

## 7. 判断规则

当不确定一条信息是否应该写入 NanoMem 时，使用下面的规则：

```text
如果 agent 以后可以可靠地从 workspace、repo、日志、对象存储或业务系统重新读取它，
不要写入 NanoMem。

如果它是跨会话、用户相关、会影响未来交互方式或理解用户背景的细粒度事实，
写入 NanoMem。
```
