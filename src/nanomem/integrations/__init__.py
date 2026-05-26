"""Host integrations layered on top of :mod:`nanomem.adapters`.

This package consumes :mod:`nanomem.adapters` to expose agent-host hook
runners (e.g. the ``nanomem-agent-hook`` entry point). The dependency
is **one-way**: integrations import from adapters, never the reverse.
Confirmed by the import-graph audit during the v0.2-alpha refactor.

If you need a new integration:

- generic adapter shape → add to :mod:`nanomem.adapters`
- a host-specific hook runner or CLI wrapper → add here
"""

from __future__ import annotations

__all__: list[str] = []
