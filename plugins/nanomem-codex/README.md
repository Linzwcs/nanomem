# NanoMem Codex Plugin

This repo-local plugin connects Codex to a running NanoMem sidecar.
It is an explicit opt-in adapter, not part of NanoMem's default system
installation.

Full installation and validation details are documented in
[`docs/plugins/codex-installation.md`](../../docs/plugins/codex-installation.md).

## Prerequisites

```bash
python -m pip install -e .
nanomem-server --config .nanomem/config.json
```

Register this repository as a local Codex marketplace, then install the plugin
from Codex `/plugins`:

```bash
codex plugin marketplace add /path/to/nanomem
```

Enable `plugin_hooks` and trust the NanoMem hooks in `/hooks` before expecting
automatic read/capture to run.

After install/trust, run the repo smoke test:

```bash
bash scripts/smoke_codex_plugin.sh
```

Set environment variables in the Codex session or shell:

```bash
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
export NANOMEM_READ_TRIGGER=submit
```

Use `NANOMEM_READ_TRIGGER=mcp` to disable automatic read injection. Prompt
spooling still runs as a separate transient hook for later capture correlation.
In that mode Codex can call MCP `nanomem_read` when long-term personal context
seems relevant.

## Behavior

- `UserPromptSubmit`: runs `nanomem-agent-hook spool --host codex` first, then
  `nanomem-agent-hook read --host codex`. `spool` writes only a transient turn
  record for the later Stop hook. `read` is pure retrieval: it injects relevant
  `PackedContext.text` when `NANOMEM_READ_TRIGGER=submit`, and returns no
  context without reading or writing when `NANOMEM_READ_TRIGGER=mcp`.
- `Stop`: runs `nanomem-agent-hook capture --host codex` and captures bounded
  user-visible dialogue. If the host provides visible user/assistant messages
  for the turn, NanoMem stores all of them and drops tool/system records. If
  only `last_assistant_message` is available, NanoMem stores the user prompt and
  that final reply. If the assistant reply is missing, automatic capture is
  skipped by default. Set `NANOMEM_CAPTURE_ASSISTANT=0` only to explicitly store
  user-only turns.
- MCP exposes `nanomem_read` only for agent-selected memory lookup. The Stop
  hook owns normal writes.

Manager/control endpoints are intentionally not exposed.
