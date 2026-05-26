"""Narrow control-plane facade for the HTTP/manager surface.

Server code (``nanomem.server.manager``) must not import
:class:`~nanomem.control.service.NanoMemControlService` directly — that
would bypass the documented ``server → service`` layer rule. Instead, the
server is handed a :class:`ControlFacade` instance with a deliberately
narrow surface: today just :meth:`stats`, with room to grow as the
manager UI needs more admin data.

The facade is read-mostly. Heavy admin actions (backup, export,
retention, reindex) still belong on the CLI/control plane and should
*not* be added here without a clear UI need.
"""

from __future__ import annotations

from nanomem.service.control.service import DatabaseStats, NanoMemControlService


class ControlFacade:
    """Read-mostly view over :class:`NanoMemControlService` for the server."""

    def __init__(self, control: NanoMemControlService) -> None:
        self._control = control

    def stats(self) -> DatabaseStats:
        """Database, index, and operation-log summary for the manager UI."""
        return self._control.stats()


__all__ = ["ControlFacade"]
