---
name: nanomem-memory
description: Use NanoMem for long-term personal memory lookup. Do not use it for repository files, tool logs, diffs, screenshots, PDFs, hidden reasoning, or writes.
---

# NanoMem Memory

Use NanoMem only for durable personal facts, preferences, corrections, and
stable user-specific collaboration context.

Prefer the hook-injected memory block when it is present. Use MCP
`nanomem_read` for manual lookup when the user asks about preferences or
long-term personal context.

MCP is read-only. The Stop hook captures visible dialogue after the assistant
response, including explicit "remember this" requests.
