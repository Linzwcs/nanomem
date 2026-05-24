---
name: nanomem-memory
description: Use NanoMem for long-term personal memory lookup. Do not use it for repository files, tool logs, diffs, screenshots, PDFs, hidden reasoning, or writes.
---

# NanoMem Memory

Use NanoMem only for durable personal facts, preferences, corrections, and
stable user-specific collaboration context.

Prefer the hook-injected memory block when it is present. If no NanoMem block is
present, use MCP `nanomem_read` when the user asks about preferences,
corrections, or long-term personal context that may affect the answer.

MCP is read-only. The Stop hook captures visible dialogue after the assistant
response, including explicit "remember this" requests.
