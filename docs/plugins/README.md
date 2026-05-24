# Agent Plugin Integration

Status: draft

This directory describes how NanoMem should integrate with agent harnesses that
support plugins, hooks, and MCP.

## Core Position

NanoMem should not use MCP as the primary storage path. MCP is useful for
agent-facing reads and explicit debugging, but capture should be a deterministic
lifecycle operation owned by the host harness or plugin hook when hooks are
available.

Recommended split:

```text
read path     -> hook-injected context or agent-selected MCP read
capture path  -> hook or wrapper calls NanoMem SDK / HTTP directly
admin path    -> CLI / control plane only
```

This keeps storage reliable, avoids model-decided duplicate writes, and prevents
maintenance operations from becoming ordinary agent tools. MCP should expose
read only; capture stays in lifecycle hooks, wrappers, SDK calls, or HTTP API
calls.

Plugin installation should be explicit and host-local. NanoMem should not
silently install Codex or Claude Code adapters into a user's system-level agent
environment; adapters become active only after the user registers, installs,
enables, and trusts them for that host.

## Shared Adapter Contract

Every plugin adapter should map host lifecycle events onto the same NanoMem
service contract:

```text
before user prompt, strategy dependent:
  spool the prompt for later capture correlation
  NanoMem.read(owner_id, namespaces, query, query_time, budget)
  inject PackedContext.text as personal memory evidence

or:
  spool the prompt and let the agent call MCP nanomem_read when needed

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
- `codex-installation.md`: Codex plugin installation, runtime flow, validation,
  and troubleshooting.
- `claude-code.md`: Claude Code plugin and hook adaptation plan.

## Repo-Local Plugin Skeletons

This repository now includes first-pass plugin packages:

```text
plugins/nanomem-codex/
plugins/nanomem-claude-code/
```

Both packages use the same installed hook runner:

```text
nanomem-agent-hook spool --host <codex|claude-code>
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
export NANOMEM_READ_TRIGGER=submit  # submit or mcp
```

If `NANOMEM_NAMESPACE` is unset or empty, the hook captures without a namespace
and reads across all namespaces.

For real host validation, set `NANOMEM_HOOK_DEBUG_DIR` temporarily:

```bash
export NANOMEM_HOOK_DEBUG_DIR=.nanomem/hook-debug
```

The hook will write raw stdin payloads there so the adapter can be adjusted to
the host's actual event JSON. Keep this off during normal use because payloads
may contain user prompts or transcript metadata.

The plugin skeletons can start `nanomem-mcp` for agent-selected memory lookup.
They should not expose capture, manager/control endpoints, raw DialogueRecord
browsing, backup, export, retention, or reindex operations as model-selected
tools.

## Design Rule

Use the strongest lifecycle primitive the harness provides:

```text
native hook > wrapper hook > explicit SDK/HTTP capture
```

MCP is for reads only. If a host has no hook support, use a wrapper or explicit
SDK/HTTP capture path rather than asking the model to write memory through MCP.
