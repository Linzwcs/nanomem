"""Operator-facing surfaces.

Five sub-packages, all aimed at humans (not agents):

- :mod:`nanomem.ops.control`        — control-plane services
  (stats, backup, export, retention, reindex)
- :mod:`nanomem.ops.maintenance`    — composed control workflows
- :mod:`nanomem.ops.cli`            — ``nanomem`` command-line tool
- :mod:`nanomem.ops.tui`            — terminal dashboard
- :mod:`nanomem.ops.manager_assets` — bundled HTML/CSS/JS assets for
  the local manager UI (served by :mod:`nanomem.transports.http.manager`)

Layering rule: ``ops/`` modules may import from :mod:`nanomem.service`,
:mod:`nanomem.pipeline`, :mod:`nanomem.core`. They must not import
:mod:`nanomem.transports` or :mod:`nanomem.hosts`.

Why these five live together: they're all surfaces an operator (not an
agent) interacts with to inspect, repair, or maintain the local
deployment.
"""

from __future__ import annotations
