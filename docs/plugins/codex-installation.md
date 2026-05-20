# Codex Plugin Installation

Status: verified locally
Last checked: 2026-05-20
Local Codex CLI: `codex-cli 0.130.0`

This document explains how to install the repo-local NanoMem Codex plugin for
explicit validation or opt-in use, how Codex loads it, and why the current hook
behavior is designed this way.

## Installation Policy

Do not treat the Codex plugin as part of NanoMem's default system
installation. The normal NanoMem install should provide the library, server,
CLI, MCP entry point, and hook runner. Codex integration should remain
repo-local and opt-in because it adds executable lifecycle hooks to a user's
Codex environment.

The recommended default is:

```text
install NanoMem package -> run sidecar/server -> choose an adapter per host
```

Only register and install `nanomem-codex` when the user explicitly wants Codex
to read/capture personal memory automatically. For development and smoke tests,
install it temporarily, validate behavior, then remove it from the Codex
environment.

## What Gets Installed

The Codex plugin is split into two layers:

```text
.agents/plugins/marketplace.json       # local marketplace catalog
plugins/nanomem-codex/
  .codex-plugin/plugin.json            # plugin manifest
  hooks.json                           # Codex lifecycle hooks
  .mcp.json                            # optional MCP tools
  skills/nanomem-memory/SKILL.md       # model-facing usage guidance
```

`codex plugin marketplace add <repo-root>` only registers the marketplace. It
does not install the plugin. Installing `nanomem-codex` copies the plugin into
Codex's cache under `~/.codex/plugins/cache/...` and writes:

```toml
[plugins."nanomem-codex@nanomem-local"]
enabled = true
```

Plugin-bundled hooks are behind Codex's `plugin_hooks` feature. On the verified
local CLI, `plugins` and `hooks` are enabled by default, while `plugin_hooks` is
available but disabled by default.

## Opt-In Installation Steps

Install NanoMem so the hook command is on `PATH`:

```bash
python -m pip install -e .
which nanomem-agent-hook
```

Start the NanoMem sidecar:

```bash
nanomem-server --config .nanomem/config.json --host 127.0.0.1 --port 8765
```

Export runtime configuration for Codex sessions:

```bash
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
```

Register the repository as a local marketplace:

```bash
codex plugin marketplace add /path/to/nanomem
```

Open Codex, use `/plugins`, select `NanoMem Local`, and install
`nanomem-codex`. Enable plugin hooks either for one run:

```bash
codex --enable plugin_hooks
```

or persist it in `~/.codex/config.toml`:

```toml
[features]
plugin_hooks = true
```

Open `/hooks` and trust both NanoMem hooks. Codex records trusted hook hashes in
`hooks.state`; hashes are content-sensitive, so use the UI again after editing
`hooks.json`.

## Runtime Flow

`UserPromptSubmit` runs before Codex sends the turn to the model:

```text
Codex prompt JSON
  -> nanomem-agent-hook read --host codex
  -> write a small turn spool record
  -> POST /v1/read
  -> return hookSpecificOutput.additionalContext
```

The injected context is wrapped in
`<nanomem_personal_memory>...</nanomem_personal_memory>` so the model sees it as
evidence, not as hidden state.

`Stop` runs after Codex has produced the final answer:

```text
Codex stop JSON
  -> nanomem-agent-hook capture --host codex
  -> load the spooled user prompt
  -> read last_assistant_message when available
  -> POST /v1/capture
```

The hook deliberately avoids parsing the full transcript. Transcript files are
useful for audit and debugging, but normal capture should use bounded,
user-visible dialogue only.

## Why These Fixes Were Needed

`marketplace.json` was added under `.agents/plugins/` because Codex discovers
local repo plugins through a marketplace root. A temporary marketplace proved
the plugin worked, but keeping the catalog in the repo makes installation
repeatable.

The docs now distinguish marketplace registration from plugin installation.
Registration makes `nanomem-codex` visible; installation is what writes the
enabled plugin entry and populates Codex's plugin cache.

Hook trust is required because Codex treats command hooks as executable code.
An installed hook can still be enabled but untrusted; in that state it appears
in `/hooks` but does not reliably execute until the user trusts its current
hash.

Assistant capture now defaults to enabled. Codex `Stop` provides
`last_assistant_message`, and NanoMem's dialogue archive should represent the
visible exchange: user prompt plus final assistant reply. This improves audit
and future extraction without storing hidden reasoning or tool output. Set
`NANOMEM_CAPTURE_ASSISTANT=0` if a deployment wants user-only capture.

The read-hook test query was made explicit because that test should verify hook
transport and context injection, not broad semantic generalization from a local
hashing embedding.

## Smoke Test

Use the repo smoke script when the plugin is already installed and trusted in
Codex:

```bash
bash scripts/smoke_codex_plugin.sh
```

The script starts a temporary NanoMem server, creates a temporary
`nanomem-agent-hook` shim for the Codex child process, runs `codex exec
--enable plugin_hooks`, and checks hook debug payloads plus SQLite state. It
does not register a marketplace, install a plugin, enable plugin hooks
persistently, or write hook trust state.

Manual validation is equivalent. Temporarily enable raw hook payload capture:

```bash
export NANOMEM_HOOK_DEBUG_DIR=.nanomem/hook-debug
```

Run a non-interactive Codex turn:

```bash
codex exec --enable plugin_hooks --json \
  'I prefer concise Chinese answers. Reply exactly OK and do not run tools.'
```

Expected evidence:

- `.nanomem/hook-debug/` contains one `codex-read-*.json` and one
  `codex-capture-*.json`.
- The read payload includes `hook_event_name: "UserPromptSubmit"` and `prompt`.
- The capture payload includes `hook_event_name: "Stop"` and
  `last_assistant_message`.
- NanoMem contains a `DialogueRecord` with user and assistant messages, plus
  extracted `MemoryUnit` rows for durable personal facts.

Disable `NANOMEM_HOOK_DEBUG_DIR` after validation because it stores raw prompt
payloads and transcript metadata.

## Troubleshooting

If no hook debug files appear, check `plugin_hooks`, `/hooks` trust state,
`which nanomem-agent-hook`, and whether the plugin is installed rather than
only listed in the marketplace.

If read returns no memory context, verify that NanoMem already has matching
memory for the same `NANOMEM_OWNER_ID` and namespace.

If capture succeeds but no assistant message appears in `DialogueRecord`, check
that `NANOMEM_CAPTURE_ASSISTANT` is not set to `0` and that the host payload
contains `last_assistant_message`.

If Codex reports a hook JSON error, ensure the hook command writes only
Codex-compliant JSON to stdout. Logs must go to stderr or NanoMem operation
logs.
