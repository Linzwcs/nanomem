"""Operator-facing surfaces.

- :mod:`nanomem.admin.cli`        — ``nanomem`` command-line tool
- :mod:`nanomem.admin.tui`        — terminal dashboard
- :mod:`nanomem.admin.manager_ui` — bundled HTML/CSS/JS for the local
                                  manager UI (served by
                                  :mod:`nanomem.transports.http.manager`)

Layering rule: ``admin/`` modules may import from :mod:`nanomem.service`,
:mod:`nanomem.pipeline`, :mod:`nanomem.core`. They must not import
:mod:`nanomem.transports` or :mod:`nanomem.hosts`.
"""

from __future__ import annotations
