# NanoMem Product RFC

Status: draft

This document defines the intended product boundary for NanoMem as a production
memory backend. It is separate from `memexp`, which remains the experiment and
evaluation platform. `memexp` may prototype and evaluate memory methods before
they are promoted into NanoMem.

For the top-level system design, see `docs/system-design.md`.

For agent-harness integration guidance, including how coding, chat, research,
multimodal, enterprise, and multi-user agents should read and write memory, see
`docs/agent-memory-positioning.md`.

For architecture diagrams, capture/read flows, and the store/index split, see
`docs/architecture-overview.md`.

## 1. Product Position

NanoMem is a long-term personal memory backend for agents.

It is designed as a sidecar database for modern agent harnesses, not as the
harness itself. Local and coding agents such as Claude Code, Codex, and
OpenClaw-like runtimes already have strong workspace tools: file reads, repo
search, terminal execution, git state, logs, artifacts, project instruction
files, and MCP tools. NanoMem should complement those tools by managing only
durable personal memory.

It is not a workspace memory system, a document memory system, a project
knowledge base, or an agent framework. Agents already have local workspace
tools for those responsibilities: filesystem reads, Markdown documents, repo
search, git history, code intelligence, logs, and artifacts.

NanoMem should cover the gap left by local files:

```text
durable, cross-session, user-specific personal fact units
```

The core product claim is:

```text
Your agent can read your workspace. NanoMem helps it remember you.
```

## 2. Core Principles

### 2.1 Do Not Become a Second Workspace

NanoMem must not replace local files, Markdown, git, or workspace search.

The following are out of scope for NanoMem:

- project docs;
- codebase knowledge;
- ADRs and design notes;
- PDFs, images, audio, video, screenshots, datasets, and other raw multimodal
  resources;
- runbooks and procedures;
- current plans and scratchpads;
- task state;
- raw tool logs;
- build or test outputs;
- meeting notes;
- repository-specific agent instructions.

Those belong in the local workspace and should be retrieved by the agent using
local tools.

Multimodal resources follow the same boundary. The agent or a tool may inspect
an image, PDF, audio clip, video, or screenshot, then surface the relevant
personal information in user-visible dialogue. NanoMem may store durable
personal facts extracted from that dialogue. It should not store, re-index, or
directly reference the raw resource as normal memory evidence.

### 2.2 Fact MemoryUnit Log, Not Truth Maintenance

For long-term personal memory, research results indicate that fact-form storage
is more suitable than raw chunk storage. However, fact-form storage does not
mean NanoMem maintains a canonical user profile.

NanoMem stores personal fact units:

```text
append-only units extracted from user-visible dialogue
```

NanoMem should not primarily perform:

- semantic deduplication;
- automatic fact update;
- automatic conflict resolution;
- latest-wins profile synthesis;
- canonical truth maintenance.

Instead, `read` returns relevant units with time and dialogue evidence.
The downstream LLM or agent decides what the current answer means in context.

### 2.3 Engineering Maintenance Is Required

The unit log cannot grow without bounds. NanoMem should perform
engineering maintenance, not semantic truth maintenance.

Allowed maintenance includes:

- retention policies;
- hot, warm, and cold storage tiers;
- explicit time filtering with recency-aware ranking;
- idempotency protection for repeated captures;
- exact duplicate suppression for replayed dialogues;
- index compaction;
- token-budget packing;
- privacy delete and redaction.

These mechanisms control storage, indexing, retrieval, and compliance. They do
not decide which conflicting fact is true.

## 3. Memory Scope

NanoMem stores only long-term personal memory.

In scope:

- user preferences;
- user communication preferences;
- stable user-specific engineering preferences;
- user corrections to agent behavior;
- personal background facts;
- relationship facts;
- cross-project user habits;
- user-relevant event facts;
- agent-interaction event facts that affect future collaboration;
- long-term interaction units that do not naturally belong in a repo.

Examples:

```text
[2026-01-05] The user prefers concise answers in Chinese.
[2026-02-12] The user usually wants a design pass before implementation.
[2026-03-20] The user prefers uv over pip in Python projects when no project
instruction says otherwise.
[2026-04-08] The user corrected the assistant not to auto-commit code.
[2026-05-19] The user decided NanoMem should focus on long-term personal
memory instead of all-in-one workspace memory.
[2026-05-19] An agent previously auto-committed code and the user reacted
negatively, so future agents should avoid auto-commit behavior.
```

Event facts are allowed when they are durable personal evidence. They may
describe what happened to the user, what the user decided, or what a visible
agent action caused in the collaboration. They are still stored as fine-grained
MemoryUnits, not as raw event streams.

### 3.1 Extraction Style

MemoryUnits should be written as third-person, evidence-grounded statements.
They should preserve who said, asked, decided, corrected, experienced, or caused
the fact.

Preferred:

```text
The user said they prefer concise Chinese answers.
The user asked the agent not to auto-commit code.
The user decided NanoMem should focus on long-term personal memory.
The agent auto-committed code and the user reacted negatively.
```

Avoid:

```text
I prefer concise Chinese answers.
Do not auto-commit code.
NanoMem should focus on long-term personal memory.
```

This keeps MemoryUnits as evidence rather than direct instructions or canonical
truth. The downstream agent can reason over time, dialogue evidence, scope, and
conflicts.

Out of scope:

```text
This repo's test command is ...
The project ADR says ...
The current task plan is ...
The CI log failed at ...
The API endpoint is documented in docs/api.md ...
The agent ran tool call abc123 with this full stdout ...
The agent edited file x during the current task ...
```

Those facts belong to the workspace, not NanoMem.

## 4. External API

The external agent-facing API should remain small:

```text
capture
read
```

The small API is a product boundary. NanoMem may have internal indexing,
retention, storage, privacy, and observability APIs, but agent frameworks should
not need them for normal operation.

### 4.1 `capture`

`capture` receives user-visible dialogue and appends extracted personal fact
units when appropriate.

Conceptual request:

```python
CaptureRequest:
  scope: MemoryScope
  dialogue: CaptureDialogue
  capture_time: str
```

Conceptual dialogue:

```python
DialogueMessage:
  role: str
  content: str
  speaker_id: str | None
  timestamp: str

CaptureDialogue:
  messages: list[DialogueMessage]
  occurred_at: str
  metadata: dict
```

`capture` should not ingest arbitrary project documents or code. If an event
contains project-local information, NanoMem should only store it when it is a
durable user-specific preference or correction.

Assistant events may be extracted, but only from final user-visible replies.
NanoMem must not capture hidden reasoning, chain-of-thought, tool calls, tool
results, or intermediate assistant planning as long-term memory.

Host-controlled log pointers or record ids belong in `metadata` when needed for
audit. NanoMem should not require host-specific concepts such as conversation id
or turn id in the core model.

When a host agent needs memory for multiple people or actors in one dialogue,
it should provide stable `speaker_id` values on messages. First-version capture
writes accepted units under the request owner and resolved namespace; unclear
speaker attribution should be skipped rather than merged into the wrong
person's memory.

### 4.2 `read`

`read` retrieves relevant personal fact units.

Conceptual request:

```python
ReadRequest:
  owner_id: str
  namespaces: tuple[str, ...] | None
  query: str | dict
  query_time: str
  time_range: TimeRange | None
  recency_policy: "recent" | "balanced" | "historical"
  max_units: int | None
  context_budget_tokens: int | None
  metadata: dict
```

When `time_range` is omitted, read should not hard-filter older memories by
default. Recency policy and `query_time` influence ranking; explicit
`time_range` is the strict time-bound mechanism.

Conceptual response:

```python
ReadResult:
  units: list[RankedMemoryUnit]
  context: PackedContext
  stats: dict
  trace_ref: str | None
```

The returned context should preserve enough evidence for the agent to reason:

- unit text;
- event timestamp and availability time;
- dialogue reference;
- scope metadata when relevant.

## 5. Data Model

NanoMem's primary record is a personal fact unit.

```python
MemoryUnit:
  unit_id: str
  scope: MemoryScope
  text: str
  memory_type: str
  timestamp: str
  available_at: str
  dialogue_refs: tuple[DialogueRef, ...]
  retention_until: str | None
  redacted_at: str | None
  metadata: dict
```

The human-readable `text` remains the primary unit payload. Structured
annotations such as subject/predicate/object, polarity, and speaker attribution
can be added later as optional aids, but they are not first-version core fields.

NanoMem should avoid fields that imply canonical truth maintenance as a default
path, such as:

```text
canonical_value
valid_to
supersedes
current_truth
```

Those may exist later as optional derived views, but they are not the primary
storage semantics.

## 6. Scope Model

NanoMem should support enough scope to isolate personal memory without taking
over workspace context.

```python
MemoryScope:
  owner_id: str
  namespace: str | None
```

`owner_id` identifies whose personal memory is being accessed. `namespace` is a
stable user- or host-defined category such as `personal`, `work`, or
`research`. Project, session, agent, and tool ids are metadata on MemoryUnits or
control-plane DialogueRecords, not core scope dimensions.

## 7. Read Semantics

Retrieval should optimize for useful evidence, not a single truth value.

At the algorithm level, NanoMem should treat user-visible dialogue as source
material, not as the retrieval unit. Capture may first split long dialogues into
bounded chunks of size `n`, then extract fact units with `role` and
`speaker_id` attribution. This keeps extraction local enough for model quality
and preserves who a fact is about or spoken by.

Read then retrieves fact units rather than raw chunks. The final renderer is an
explicit optimization stage: under the same post-render token budget, it should
include as many high-value facts as possible while preserving the timestamp for
each rendered fact. Other displayed labels, such as dialogue refs, namespace,
memory type, tags, and project hints, are renderer-configurable metadata. This
means render quality is measured not only by readability, but also by fact
density after formatting overhead.

Recommended ranking signals:

- query relevance;
- recency;
- scope match;
- evidence quality;
- unit type;
- historical-intent detection.

Rendering must preserve timeline cues. For example:

```text
Relevant memory units:
- [2026-01-05] The user said they usually use pip.
- [2026-04-18, project=current] The user said this project should use uv and not pip.
```

The agent can then infer that the later project-specific instruction should
control the current project.

## 8. Maintenance Policies

NanoMem should expose retention and retrieval policies at the engineering
level.

Example policy:

```text
recent policy: boosts newer facts without hiding older ones
historical policy: gives older relevant facts more room
cold archive: optional, not searched by default
hard delete: tenant policy or privacy request
```

Maintenance jobs may:

- move units between tiers;
- rebuild indexes;
- compact storage files;
- remove records past retention;
- redact deleted dialogue evidence;
- preserve audit records where allowed.

Operators also need a read-only inspection surface. The first TUI should show
database detail, recent MemoryUnits, and recent capture/read logs, including
retrieval queries, ranked units, and NanoMem's rendered response context.
The database should expose schema version information, and operation logs should
have a separate retention path from MemoryUnits. Operators also need physical
SQLite backups, logical JSON exports for inspection, schema migration status,
and integrity checks. A maintenance runner should turn those individual
operations into a config-driven `plan` and explicitly confirmed `run`.

Maintenance jobs should not silently merge units into a canonical
profile.

## 9. Agent Integration

An OpenClaw-like agent should integrate NanoMem as a personal-memory sidecar:

```text
before_turn:
  local context = agent reads workspace files and logs
  personal context = NanoMem.read(query, scope)

after_turn:
  NanoMem.capture(user-facing events, scope)
```

The preferred integration shape is a thin SDK plus lifecycle adapter. The SDK
only exposes the normal memory operations, while adapters translate host-agent
turn hooks into `CaptureRequest` and `ReadRequest`.

MCP integration should follow the same boundary. It may expose `nanomem_read`
and `nanomem_capture` tools for MCP-capable hosts, but it should not expose
maintenance, database, or workspace-search tools to agents.

The agent remains responsible for:

- reading project docs;
- searching code;
- inspecting logs;
- maintaining task plans;
- following repo instructions;
- deciding how to use returned personal units.

NanoMem remains responsible for:

- extracting personal units;
- storing them durably;
- explicit time filtering and recency-aware ranking;
- evidence rendering;
- retention and privacy controls.

## 10. Relationship To `memexp`

`memexp` is the experiment platform. NanoMem is the production memory backend.

The intended flow is:

```text
research idea
  -> memexp prototype
  -> benchmark and ablation
  -> promotion decision
  -> NanoMem implementation
  -> memexp regression
  -> production release
```

For the current long-term personal memory research result:

```text
fact-form units are the preferred storage shape
```

`memexp` should continue to evaluate:

- fact extraction quality;
- read accuracy;
- time-window behavior;
- context budget behavior;
- dialogue trace usefulness;
- comparison with raw-message or chunk baselines.

## 11. First Implementation Slice

The first production-oriented slice should be intentionally small:

1. `capture` accepts messages and corrections.
2. `capture` extracts personal fact units only.
3. MemoryUnits are appended to a durable store.
4. `read` retrieves units with owner/namespace filtering and recency-aware ranking.
5. `read` returns structured units and rendered evidence context.
6. Local docs, code, runbooks, plans, and logs remain out of scope.

This slice should be enough to validate the product boundary with an
OpenClaw-like agent without building a broad memory platform.
First-version capture does not include idempotency. Hosts should avoid
replaying completed captures; retry-safe idempotency can be added later outside
the MemoryUnit/read semantics.
