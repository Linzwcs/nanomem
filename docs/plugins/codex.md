# Codex Adapter Plan

Status: draft
Last checked: 2026-05-20

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

Use Codex hooks for deterministic lifecycle work and MCP only as an optional
agent-facing read/debug tool.

```text
UserPromptSubmit hook:
  call NanoMem.read directly
  emit personal-memory context for Codex

Stop hook:
  call NanoMem.capture directly
  store only user-visible dialogue

MCP server:
  expose nanomem_read for ad hoc lookup
  expose nanomem_capture only for explicit "remember this" commands
```

Capture should call NanoMem through the local SDK, in-process service, or HTTP
API. It should not go through MCP because automatic storage should not be a
model-selected tool call.

## Hook Data Flow

Codex `UserPromptSubmit` receives the user prompt. The hook should:

1. resolve `owner_id` and namespace from config;
2. call `NanoMem.read` with the prompt as query;
3. keep a small turn spool record containing the prompt, timestamp, and a
   generated turn id;
4. return a compact memory block as additional prompt context.

Codex `Stop` receives the final assistant message. The hook should:

1. load the matching turn spool record;
2. build a bounded `CaptureDialogue` from the user prompt and final assistant
   reply;
3. call `NanoMem.capture` with the bounded dialogue;
4. return success without adding user-visible text.

Avoid parsing full transcripts for the normal path. Transcript files can be
unstable across harness versions and may contain more material than NanoMem
should capture.

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
            "command": "python scripts/nanomem_codex_read.py"
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
nanomem-agent-hook read --host codex
nanomem-agent-hook capture --host codex
```

The command talks to a running NanoMem server over HTTP. Configure it with:

```bash
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
```

If `NANOMEM_NAMESPACE` is unset or empty, the hook captures without a namespace
and reads all namespaces.

## What Codex Should Read And Capture

| Situation | Path |
| --- | --- |
| User asks about current repo files | Codex reads workspace directly |
| User asks something affected by personal preferences | Hook or MCP calls `nanomem_read` |
| User gives a stable preference | Stop hook captures visible dialogue |
| User corrects agent behavior | Stop hook captures visible dialogue |
| Codex tool stdout, git diff, logs, files | Do not capture |
| User explicitly says "remember this" | MCP `nanomem_capture` may be used |

## Failure Policy

Read hook failure should not block Codex. It should return no memory context and
log the failure.

Capture hook failure should not change the assistant response. It should record
an operation log or local retry item. First-version NanoMem does not provide
capture idempotency, so retry queues should avoid replaying completed captures.
