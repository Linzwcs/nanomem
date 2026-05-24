# Codex Integration Installation

Status: interactive hook validation passed
Last checked: 2026-05-24
Local Codex CLI: `codex-cli 0.133.0`

This document explains how to install NanoMem's project-level Codex hooks, how
to validate the hook data flow, and how the repo-local Codex plugin fits in as
an optional packaging layer.

Current local validation shows that interactive Codex loads project-level hooks,
asks for hook trust, runs `UserPromptSubmit`, and produces NanoMem
`spool/read/capture` payloads. The same local `codex exec` path did not execute
project, user, or plugin-bundled hooks, so do not use non-interactive
`codex exec` alone as proof that hooks are active.

## Installation Policy

Do not treat the Codex plugin as part of NanoMem's default system
installation. The normal NanoMem install should provide the library, server,
CLI, MCP entry point, and hook runner. Codex integration should remain
repo-local and opt-in because it adds executable lifecycle hooks to a user's
Codex environment.

The recommended default is:

```text
install NanoMem package -> install project hooks -> run sidecar/server
```

Only register and install `nanomem-codex` when the user explicitly wants Codex
to use NanoMem plugin packaging for skills or future plugin-hook support. For
development and smoke tests, install it temporarily, validate behavior, then
remove it from the Codex environment. Do not assume plugin-bundled hooks will
run until the plugin smoke test proves it.

## What Gets Installed

NanoMem's Codex integration has two layers:

```text
.codex/hooks.json                     # project-level executable hooks
.agents/plugins/marketplace.json       # local marketplace catalog
plugins/nanomem-codex/
  .codex-plugin/plugin.json            # plugin manifest
  hooks/hooks.json                     # plugin-bundled hook template
  .mcp.json                            # optional read-only MCP config template
  skills/nanomem-memory/SKILL.md       # model-facing usage guidance
```

`nanomem install-codex-hooks --project-dir .` writes the project hook file.

`codex plugin marketplace add <repo-root>` only registers the marketplace. It
does not install the plugin. Installing `nanomem-codex` copies the plugin into
Codex's cache under `~/.codex/plugins/cache/...` and writes:

```toml
[plugins."nanomem-codex@nanomem-local"]
enabled = true
```

Plugin-bundled hooks are behind Codex's `plugin_hooks` feature. On the checked
local CLI, `plugins`, `hooks`, and `plugin_hooks` are feature-available.
Project-level hooks use the normal Codex hook layer and were verified in
interactive Codex after trusting hooks. Local `codex exec` did not execute
project or user hooks in the checked environment.

NanoMem's MCP entry point exposes `nanomem_read` only. In hook-based Codex use,
normal turn storage belongs to the Stop hook, avoiding model-selected duplicate
capture of the same visible dialogue.

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
export NANOMEM_READ_TRIGGER=submit
```

`NANOMEM_READ_TRIGGER=submit` reads memory at `UserPromptSubmit` and injects a
memory block automatically. Set `NANOMEM_READ_TRIGGER=mcp` when you want the hook
to skip automatic read injection and let Codex decide whether to call MCP
`nanomem_read`. Prompt spooling is a separate hook action used only for later
capture correlation.

Install project-level hooks in the repository:

```bash
nanomem install-codex-hooks --project-dir .
```

This writes `.codex/hooks.json` with:

```text
UserPromptSubmit -> nanomem-agent-hook spool --host codex
UserPromptSubmit -> nanomem-agent-hook read --host codex
Stop             -> nanomem-agent-hook capture --host codex
```

Optional: register the repository as a local marketplace:

```bash
codex plugin marketplace add /path/to/nanomem
```

Open Codex, use `/plugins`, select `NanoMem Local`, and install
`nanomem-codex` only if you want the plugin skill/package. Enable plugin hooks
either for one run:

```bash
codex --enable plugin_hooks
```

or persist it in `~/.codex/config.toml`:

```toml
[features]
plugin_hooks = true
```

Open `/hooks` and trust both NanoMem hooks when using interactive hooks.
Codex records trusted hook hashes in `hooks.state`; hashes are
content-sensitive, so use the UI again after editing `.codex/hooks.json` or
`hooks/hooks.json`.

Do not enable project-level hooks and plugin-bundled hooks at the same time
unless you intentionally want both hook sets. In the local verification run,
Codex reported four `UserPromptSubmit` hooks because the project hooks and an
installed plugin hook template were both present.

## Runtime Flow

`UserPromptSubmit` runs before Codex sends the turn to the model. In submit
mode:

```text
Codex prompt JSON
  -> nanomem-agent-hook spool --host codex
  -> write a small transient turn spool record
  -> nanomem-agent-hook read --host codex
  -> POST /v1/read
  -> return hookSpecificOutput.additionalContext
```

In MCP mode, `nanomem-agent-hook spool` still writes the transient turn record,
but `nanomem-agent-hook read` returns success without reading or writing. The
agent can then call MCP `nanomem_read` only when memory seems relevant.

The injected context is wrapped in
`<nanomem_personal_memory>...</nanomem_personal_memory>` so the model sees it as
evidence, not as hidden state.

`Stop` runs after Codex has produced the final answer:

```text
Codex stop JSON
  -> nanomem-agent-hook capture --host codex
  -> load the spooled user prompt
  -> use visible user/assistant messages when available
  -> otherwise read last_assistant_message when available
  -> POST /v1/capture
```

The hook deliberately avoids parsing hidden reasoning, tool stdout, or raw
transcript files for the normal path. If the host provides a bounded visible
message list for the turn, NanoMem captures all user and assistant messages in
that list and drops tool/system records. If the host only provides
`last_assistant_message`, NanoMem stores the user prompt plus that final reply.

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

Project-level hook installation was added because official Codex hooks are the
right lifecycle primitive for NanoMem capture. The generated `.codex/hooks.json`
keeps the executable lifecycle path explicit and does not require installing
NanoMem into the system-wide Codex plugin cache. Interactive Codex validation
confirmed that this layer is loaded and run after hook trust.

Assistant capture now defaults to enabled. NanoMem's dialogue archive should
represent the visible exchange: the user prompt plus all visible assistant
messages the host exposes for the turn. This improves audit and future
extraction without storing hidden reasoning or tool output. If assistant capture
is enabled and the host payload does not include any assistant response, the
hook skips automatic capture instead of storing a partial user-only dialogue.
Set `NANOMEM_CAPTURE_ASSISTANT=0` only if a deployment explicitly wants
user-only capture.

The read-hook test query was made explicit because that test should verify hook
transport and context injection, not broad semantic generalization from a local
hashing embedding.

## Sidecar Smoke Test

Use the sidecar smoke test before installing the Codex plugin. It simulates the
Codex hook JSON contract, calls the same hook runner, writes through the local
HTTP sidecar, restarts the sidecar, and verifies that SQLite-persisted memory is
still searchable.

```bash
bash scripts/smoke_codex_sidecar.sh
```

This script does not require the Codex CLI. It validates NanoMem's side of the
integration: `UserPromptSubmit -> spool/read`, `Stop -> capture`, SQLite
persistence, startup reindex, and rendered read context.

## Codex Project-Hook Smoke Test

Use the project-hook smoke test as a non-interactive diagnostic for Codex's
normal hook layer without installing the plugin:

```bash
bash scripts/smoke_codex_project_hooks.sh
```

The script starts a temporary NanoMem server, writes `.codex/hooks.json`,
creates a temporary `nanomem-agent-hook` shim for the Codex child process, runs
`codex exec` with hook trust bypassed for that invocation, and restores the
original hook file on exit.

On the checked local CLI, this diagnostic currently fails because `codex exec`
does not emit hook payloads even for a minimal user-level hook. That result
means the non-interactive smoke cannot validate hooks here; it does not change
the verified interactive hook behavior.

## Codex Plugin Smoke Test

Use the repo smoke script when the plugin is already installed in Codex:

```bash
bash scripts/smoke_codex_plugin.sh
```

The script starts a temporary NanoMem server, creates a temporary
`nanomem-agent-hook` shim for the Codex child process, runs `codex exec` with
plugin hooks enabled and hook trust bypassed for that invocation, and checks
hook debug payloads plus SQLite state. It does not register a marketplace,
install a plugin, enable plugin hooks persistently, or write hook trust state.

On `codex-cli 0.133.0`, this smoke currently loads the plugin skill but does
not observe plugin hook execution. Treat that as a non-interactive Codex
adapter limitation, not a NanoMem store/read failure.

## Interactive Codex Verification

The verified local flow used a real TTY and the `codex` main command, not
`codex exec`:

```bash
nanomem install-codex-hooks --project-dir .
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
export NANOMEM_HOOK_DEBUG_DIR=.nanomem/hook-debug
codex --enable hooks --dangerously-bypass-hook-trust
```

Expected evidence:

- Codex shows `Hooks need review`; choose `Trust all and continue` or review
  the NanoMem commands manually.
- During a submitted prompt, Codex shows `Running ... UserPromptSubmit hooks`.
- `.nanomem/hook-debug/` receives `codex-spool`, `codex-read`, and
  `codex-capture` JSON payloads.
- The NanoMem database receives a `DialogueRecord`. If the hook payload has no
  `session_id`, MemoryUnits are extracted immediately. If it has `session_id`,
  units become searchable after the window reaches the token limit or after
  `nanomem flush`.

Local verification on 2026-05-24 produced one dialogue and two memory units.

Manual validation is equivalent when the chosen Codex mode executes hooks.
Temporarily enable raw hook payload capture:

```bash
export NANOMEM_HOOK_DEBUG_DIR=.nanomem/hook-debug
```

Run a non-interactive Codex turn only if that mode supports hooks in your CLI:

```bash
codex exec --enable hooks \
  --dangerously-bypass-hook-trust --json \
  'I prefer concise Chinese answers. Reply exactly OK and do not run tools.'
```

Expected evidence:

- `.nanomem/hook-debug/` contains one `codex-spool-*.json`, one
  `codex-read-*.json`, and one
  `codex-capture-*.json`.
- The read payload includes `hook_event_name: "UserPromptSubmit"` and `prompt`.
- The capture payload includes `hook_event_name: "Stop"` and
  `last_assistant_message`.
- NanoMem contains a `DialogueRecord` with user and assistant messages. Durable
  facts appear as `MemoryUnit` rows immediately for one-shot capture, or after
  flushing for buffered session capture.

If `codex exec` produces no hook payloads, switch to interactive Codex and
validate with `/hooks`; the local checked CLI behaved this way.

Disable `NANOMEM_HOOK_DEBUG_DIR` after validation because it stores raw prompt
payloads and transcript metadata.

## Troubleshooting

If no hook debug files appear for project hooks, check that `.codex/hooks.json`
exists in the Codex working directory, hook trust is satisfied or bypassed, and
`nanomem-agent-hook` is reachable from Codex's `PATH`.

If no hook debug files appear for plugin-bundled hooks, check whether the target
Codex mode executes plugin hooks at all. Then check `plugin_hooks`, `/hooks`
trust state, and whether the plugin is installed rather than only listed in the
marketplace.

If Codex reports `MCP startup incomplete (failed: nanomem)` while using
project-level hooks, disable or reinstall the cached `nanomem-codex` plugin
before diagnosing hooks. A stale installed plugin may still point MCP at a
missing `.nanomem/config.json`; hook capture/read does not require MCP.

If read returns no memory context, verify that NanoMem already has matching
memory for the same `NANOMEM_OWNER_ID` and namespace.

If capture succeeds but no assistant message appears in `DialogueRecord`, check
that `NANOMEM_CAPTURE_ASSISTANT` is not set to `0` and that the host payload
contains `last_assistant_message`.

If Codex reports a hook JSON error, ensure the hook command writes only
Codex-compliant JSON to stdout. Logs must go to stderr or NanoMem operation
logs.
