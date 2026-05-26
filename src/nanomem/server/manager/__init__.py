"""Control-plane HTTP surface (``/manager/*``).

The manager is **not** an agent-facing surface — it powers the local
operator UI and admin endpoints. Never expose it to untrusted networks.

Public dispatch lives in :mod:`nanomem.server.manager.routes`
(:func:`handle_manager_get`, :func:`handle_manager_post`,
:class:`ManagerResponse`). It is re-exported here so existing
``from nanomem.server.manager import handle_manager_get`` import sites
continue to work.
"""

from __future__ import annotations

from nanomem.server.manager.routes import (
    ManagerResponse,
    handle_manager_get,
    handle_manager_post,
)


__all__ = [
    "ManagerResponse",
    "handle_manager_get",
    "handle_manager_post",
]
