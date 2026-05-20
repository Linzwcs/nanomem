# Agent Plugin Integration

Status: draft

This directory describes how NanoMem should integrate with agent harnesses that
support plugins, hooks, and MCP.

## Core Position

NanoMem should not use MCP as the primary storage path. MCP is useful for
agent-facing reads and explicit debugging, but automatic capture should be a
deterministic lifecycle operation owned by the host harness or plugin hook.

Recommended split:

```text
read path     -> hook-injected context, with optional MCP read tool
capture path  -> hook or wrapper calls NanoMem SDK / HTTP directly
admin path    -> CLI / control plane only
```

This keeps storage reliable, avoids model-decided writes, and prevents
maintenance operations from becoming ordinary agent tools.

## Shared Adapter Contract

Every plugin adapter should map host lifecycle events onto the same NanoMem
service contract:

```text
before user prompt:
  NanoMem.read(owner_id, namespaces, query, query_time, budget)
  inject PackedContext.text as personal memory evidence

after assistant response:
  collect user-visible dialogue only
  NanoMem.capture(scope, dialogue)
```

Adapters must not capture hidden reasoning, tool calls, raw tool results,
workspace files, logs, diffs, screenshots, PDFs, or complete transcripts as
MemoryUnits. If those resources matter, the agent should surface the durable
personal fact in visible dialogue; NanoMem then captures from the dialogue.

## Documents

- `codex.md`: Codex plugin, hook, and MCP adaptation plan.
- `claude-code.md`: Claude Code plugin and hook adaptation plan.

## Repo-Local Plugin Skeletons

This repository now includes first-pass plugin packages:

```text
plugins/nanomem-codex/
plugins/nanomem-claude-code/
```

Both packages use the same installed hook runner:

```text
nanomem-agent-hook read --host <codex|claude-code>
nanomem-agent-hook capture --host <codex|claude-code>
```

Required runtime setup:

```bash
python -m pip install -e .
nanomem-server --config .nanomem/config.json
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
```

If `NANOMEM_NAMESPACE` is unset or empty, the hook captures without a namespace
and reads across all namespaces.

The plugin skeletons expose `/v1/read` and `/v1/capture` only. They do not
expose manager/control endpoints, raw DialogueRecord browsing, backup, export,
retention, or reindex operations.

## Design Rule

Use the strongest lifecycle primitive the harness provides:

```text
native hook > wrapper hook > manual MCP capture
```

MCP capture is acceptable only for explicit user commands such as "remember
this", not for background storage.
