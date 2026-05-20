# Claude Code Adapter Plan

Status: draft
Last checked: 2026-05-20

## Platform Facts

Claude Code has first-class plugin support. A plugin can package custom slash
commands, agents, hooks, skills, and MCP servers. Claude Code hooks can run at
lifecycle points such as user prompt submission and session stop, which makes
them suitable for NanoMem read injection and deterministic capture.

References:

- Claude Code plugins: https://code.claude.com/docs/en/plugins
- Claude Code plugin marketplace: https://code.claude.com/docs/en/discover-plugins
- Claude Code hooks: https://code.claude.com/docs/en/hooks

## Recommended Integration

Use a native Claude Code plugin as the primary integration.

```text
UserPromptSubmit hook:
  call NanoMem.read directly
  inject PackedContext.text as additional context

Stop hook:
  call NanoMem.capture directly
  store bounded user-visible dialogue

MCP server:
  optional nanomem_read / explicit nanomem_capture tools
```

The important choice is that capture is done by the hook command, not by asking
Claude to call an MCP tool. MCP remains useful for manual lookup or explicit
"remember this" commands, but automatic storage should be deterministic and
outside the model's tool-selection loop.

## Plugin Layout

Recommended package shape:

```text
nanomem-claude-code/
  .claude-plugin/plugin.json
  hooks.json
  .mcp.json
  skills/nanomem-memory/SKILL.md
  bin/nanomem-claude-read
  bin/nanomem-claude-capture
  README.md
```

The plugin should expose only normal memory operations to Claude Code. Backup,
export, retention, deletion, reindex, and DialogueRecord inspection remain CLI
or control-plane operations.

## Hook Data Flow

`UserPromptSubmit` should:

1. read the submitted prompt from hook input;
2. resolve the NanoMem owner and namespace from plugin config;
3. call `NanoMem.read` with a small post-render token budget;
4. return a compact personal memory block as additional context.

`Stop` should:

1. read the final visible assistant message from hook input;
2. pair it with the user-visible prompt captured at `UserPromptSubmit`;
3. build a bounded `CaptureDialogue`;
4. call `NanoMem.capture` through SDK, local service, or HTTP;
5. record local retry state only if the host needs recovery.

The normal capture path should not ingest the full transcript. Full transcripts,
tool output, and hidden reasoning may include material that NanoMem should not
store.

## Example Hook Shape

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "nanomem-claude-read"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "nanomem-claude-capture",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

The command hooks should read JSON from stdin. Read hooks may emit context for
Claude. Capture hooks should be quiet on success and write diagnostics to
stderr or NanoMem operation logs.

The repo-local skeleton uses the shared command:

```text
nanomem-agent-hook read --host claude-code
nanomem-agent-hook capture --host claude-code
```

The command talks to a running NanoMem server over HTTP. Configure it with:

```bash
export NANOMEM_BASE_URL=http://127.0.0.1:8765
export NANOMEM_OWNER_ID="$USER"
export NANOMEM_NAMESPACE=personal
```

If `NANOMEM_NAMESPACE` is unset or empty, the hook captures without a namespace
and reads all namespaces.

## MCP Role

The plugin may also provide an MCP server:

```text
nanomem_read
nanomem_capture
```

Recommended policy:

- `nanomem_read`: enabled for ad hoc user-memory lookup.
- `nanomem_capture`: enabled only for explicit user requests such as "remember
  this"; automatic capture stays in hooks.
- no admin tools through MCP.

## What Claude Code Should Read And Capture

| Situation | Path |
| --- | --- |
| Current repository state | Claude Code workspace tools |
| Project-specific rules | Files such as README or AGENTS.md |
| User preference or correction | NanoMem capture hook |
| User-visible agent behavior that affects future collaboration | NanoMem capture hook |
| Tool logs, diffs, stdout, screenshots, PDFs | Do not capture |
| Manual memory lookup | Optional MCP `nanomem_read` |

## Failure Policy

Read failure should degrade to no injected memory. The user prompt should still
proceed.

Capture failure should not affect the assistant's completed answer. The hook
should record enough local state for retry. First-version NanoMem does not
provide capture idempotency, so retry queues should avoid replaying completed
captures.
