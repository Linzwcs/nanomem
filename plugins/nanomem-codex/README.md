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
```

## Behavior

- `UserPromptSubmit`: runs `nanomem-agent-hook read --host codex` and injects
  relevant `PackedContext.text`.
- `Stop`: runs `nanomem-agent-hook capture --host codex` and captures bounded
  user-visible dialogue, including the final assistant reply when Codex provides
  it. Set `NANOMEM_CAPTURE_ASSISTANT=0` to store only the user message.
- MCP tools expose only `nanomem_read` and explicit `nanomem_capture`.

Manager/control endpoints are intentionally not exposed.
