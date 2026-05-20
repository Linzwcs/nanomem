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

- `UserPromptSubmit`: runs `nanomem-agent-hook read --host claude-code` and
  injects relevant `PackedContext.text`.
- `Stop`: runs `nanomem-agent-hook capture --host claude-code` and captures
  bounded user-visible dialogue.
- MCP tools expose only `nanomem_read` and explicit `nanomem_capture`.

Manager/control endpoints are intentionally not exposed.
