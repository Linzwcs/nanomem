"""External-harness integration.

- :mod:`nanomem.hosts.adapters` — generic adapter shapes
  (``AgentMemoryAdapter``, ``AgentMessage``, ``NanoMemBackend``) plus
  the MCP server adapter.
- :mod:`nanomem.hosts.plugins`  — higher-level host integrations that
  consume :mod:`nanomem.hosts.adapters` (was ``nanomem.integrations``
  in v0.2.x; renamed for clarity since the contents are agent-harness
  plugins, not generic integrations).

Layering rule: ``hosts/`` is the highest layer — it may import from
:mod:`nanomem.service`, :mod:`nanomem.transports`, :mod:`nanomem.admin`,
:mod:`nanomem.pipeline`, :mod:`nanomem.core`.
"""

from __future__ import annotations
