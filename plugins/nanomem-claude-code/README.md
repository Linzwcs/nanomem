# NanoMem Claude Code Plugin

This repo-local plugin connects Claude Code to a running NanoMem sidecar.

## Prerequisites

```bash
python -m pip install -e .
nanomem-server --config .nanomem/config.json
```

Set environment variables in the Claude Code session or shell:

```bash
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
```

## Behavior

- `UserPromptSubmit`: runs `nanomem-agent-hook spool --host claude-code` first,
  then `nanomem-agent-hook read --host claude-code`. `spool` writes only a
  transient turn record for the later Stop hook. `read` is pure retrieval and
  injects relevant `PackedContext.text` when automatic read is enabled.
- `Stop`: runs `nanomem-agent-hook capture --host claude-code` and captures
  bounded user-visible dialogue.
- MCP exposes `nanomem_read` only for agent-selected memory lookup. The Stop
  hook owns normal writes.

Manager/control endpoints are intentionally not exposed.
