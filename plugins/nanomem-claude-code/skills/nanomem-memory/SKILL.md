---
name: nanomem-memory
description: Use NanoMem for long-term personal memory lookup and explicit remember-this capture. Do not use it for repository files, tool logs, diffs, screenshots, PDFs, or hidden reasoning.
---

# NanoMem Memory

Use NanoMem only for durable personal facts, preferences, corrections, and
stable user-specific collaboration context.

Prefer the hook-injected memory block when it is present. Use MCP
`nanomem_read` for manual lookup when the user asks about preferences or
long-term personal context.

Use MCP `nanomem_capture` only when the user explicitly asks to remember
something. Do not capture workspace files, tool output, raw logs, or complete
transcripts.
