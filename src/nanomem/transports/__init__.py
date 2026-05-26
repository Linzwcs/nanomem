"""Wire-format surfaces for agent harnesses.

Three sub-packages, one per protocol:

- :mod:`nanomem.transports.http` — stdlib ``ThreadingHTTPServer``
  exposing the agent-facing ``/v1/*`` data plane and the operator
  ``/manager/*`` control plane.
- :mod:`nanomem.transports.mcp`  — stdio MCP server exposing the
  read-only ``nanomem_read`` tool.
- :mod:`nanomem.transports.sdk`  — sync + async HTTP clients
  (``NanoMemClient``, ``AsyncNanoMemClient``).

Layering rule: ``transports/`` modules may import from
:mod:`nanomem.service`, :mod:`nanomem.pipeline`, :mod:`nanomem.core`.
They must not import :mod:`nanomem.admin` or :mod:`nanomem.hosts`.
"""

from __future__ import annotations
