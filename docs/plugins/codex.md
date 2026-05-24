# Codex Adapter Plan

Status: draft
Last checked: 2026-05-20

For the concrete installation runbook, validation steps, and rationale for the
current hook behavior, see
[`codex-installation.md`](codex-installation.md).

## Platform Facts

Codex supports MCP servers, hooks, and plugins. On the current local CLI,
`plugins` and `hooks` are enabled, while `plugin_hooks` is still under
development and disabled by default. Codex plugins can bundle skills, MCP
servers, apps, and hooks, but plugin-bundled hooks require the user to enable:

```toml
[features]
plugin_hooks = true
```

For NanoMem, this means a Codex plugin can be offered, but the default reliable
integration should not depend on plugin hooks being enabled.

References:

- Codex plugins: https://developers.openai.com/codex/plugins/
- Codex plugin build guide: https://developers.openai.com/codex/plugins/build/
- Codex hooks: https://developers.openai.com/codex/hooks/
- Codex MCP: https://developers.openai.com/codex/mcp/

## Recommended Integration

Use Codex hooks for deterministic capture. For read, choose one of two
strategies per deployment:

```text
submit read:
  run a separate spool hook at UserPromptSubmit
  call NanoMem.read directly
  emit personal-memory context for Codex

mcp read:
  run a separate spool hook at UserPromptSubmit
  let the agent call MCP nanomem_read when memory may matter

Stop hook:
  call NanoMem.capture directly
  store only user-visible dialogue

MCP server:
  expose nanomem_read for ad hoc lookup
  do not expose capture or admin tools
```

The submit strategy is deterministic and useful when user preferences should be
available before every answer. The MCP strategy avoids injecting memory into
unrelated turns and lets the agent decide when long-term personal context is
worth the extra lookup.

`nanomem-agent-hook read` is read-only. Prompt spooling is a separate hook action
used only to let the later Stop hook pair `last_assistant_message` with the
submitted prompt.

Capture should still call NanoMem through the local SDK, in-process service, or
HTTP API in the automatic hook path. MCP is read-only by design, so storage is
not a model-selected tool call.

## Hook Data Flow

Codex `UserPromptSubmit` receives the user prompt. In `submit` mode, the hook
should:

1. resolve `owner_id` and namespace from config;
2. run `nanomem-agent-hook spool` to keep a small transient turn record
   containing the prompt, timestamp, and generated turn id;
3. run `nanomem-agent-hook read` to call `NanoMem.read` with the prompt as
   query;
4. return a compact memory block as additional prompt context.

In `mcp` mode, the separate spool action still keeps the transient turn record,
but `nanomem-agent-hook read` returns success without reading or writing. The
model can then use MCP `nanomem_read` when the task seems affected by durable
personal memory.

Codex `Stop` receives the final assistant message. The hook should:

1. load the matching turn spool record;
2. build a bounded `CaptureDialogue` from visible user and assistant messages
   when the host exposes them;
3. call `NanoMem.capture` with the bounded dialogue;
4. return success without adding user-visible text.

If only `last_assistant_message` is available, the hook stores the spooled user
prompt plus that final reply. If no assistant reply is available, automatic
capture should skip the turn instead of storing a partial user-only dialogue.
User-only capture is an explicit opt-in mode for deployments that set
`NANOMEM_CAPTURE_ASSISTANT=0`.

Avoid parsing hidden reasoning, tool stdout, or raw transcript files for the
normal path. Transcript files can be unstable across harness versions and may
contain more material than NanoMem should capture.

## Suggested Local Layout

```text
.codex/
  hooks.json

.nanomem/
  codex-turns/
  nanomem.db
```

Example hook shape:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "nanomem-agent-hook spool --host codex"
          },
          {
            "type": "command",
            "command": "nanomem-agent-hook read --host codex"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/nanomem_codex_capture.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

The scripts should read the hook JSON from stdin and write hook-compliant JSON
to stdout. They should not print logs to stdout; logs belong on stderr or in
NanoMem operation logs.

## Optional Codex Plugin

A Codex plugin can package the MCP server and helper scripts:

```text
.agents/plugins/marketplace.json
plugins/nanomem-codex/
  .codex-plugin/plugin.json
  .mcp.json
  hooks.json
  skills/nanomem-memory/SKILL.md
  bin/nanomem-codex-read
  bin/nanomem-codex-capture
```

This is useful for distribution, but it should be documented as an opt-in path
because plugin hooks require `plugin_hooks = true`. The stable first path should
remain user or project hooks plus direct SDK/HTTP capture.

The repo-local skeleton uses the shared command:

```text
nanomem-agent-hook spool --host codex
nanomem-agent-hook read --host codex
nanomem-agent-hook capture --host codex
```

The command talks to a running NanoMem server over HTTP. Configure it with:

```bash
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
export NANOMEM_READ_TRIGGER=submit  # submit or mcp
```

If `NANOMEM_NAMESPACE` is unset or empty, the hook captures without a namespace
and reads all namespaces.

Local installation flow:

```bash
codex plugin marketplace add /path/to/nanomem
```

Then install `nanomem-codex` from the Codex `/plugins` UI, enable
`plugin_hooks`, and trust the two NanoMem hooks in `/hooks`. Plugin install
copies the plugin into Codex's plugin cache and writes:

```toml
[plugins."nanomem-codex@nanomem-local"]
enabled = true
```

For `codex exec` smoke tests, ensure `nanomem-agent-hook` is on `PATH` and pass
the same `NANOMEM_*` environment variables. By default the capture hook stores
the final assistant reply when Codex provides it; set
`NANOMEM_CAPTURE_ASSISTANT=0` to store only the user message.

The Codex plugin exposes MCP for `nanomem_read` only. The Stop hook owns normal
capture, so the same visible turn is not stored twice.

## What Codex Should Read And Capture

| Situation | Path |
| --- | --- |
| User asks about current repo files | Codex reads workspace directly |
| User asks something affected by personal preferences | Submit hook or MCP `nanomem_read` |
| Memory is rarely relevant for this workspace | Set `NANOMEM_READ_TRIGGER=mcp` |
| User gives a stable preference | Stop hook captures visible dialogue |
| User corrects agent behavior | Stop hook captures visible dialogue |
| Codex tool stdout, git diff, logs, files | Do not capture |
| User explicitly says "remember this" | Let the Stop hook capture the visible request |

## Failure Policy

Read hook failure should not block Codex. It should return no memory context and
log the failure.

Capture hook failure should not change the assistant response. It should record
an operation log or local retry item. First-version NanoMem does not provide
capture idempotency, so retry queues should avoid replaying completed captures.
