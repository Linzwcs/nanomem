"""Terminal UI for the nanomem control plane.

Status: experimental. The dashboard is wired into the CLI via
``nanomem dashboard`` and is intended for **operators** inspecting
local state, not for agent-facing tools. Public API may shift.
"""

from __future__ import annotations

from nanomem.ops.tui.dashboard import (
    DashboardSnapshot,
    MonitorHealth,
    build_dashboard,
    render_dashboard,
    run_dashboard_watch,
)

__all__ = [
    "DashboardSnapshot",
    "MonitorHealth",
    "build_dashboard",
    "render_dashboard",
    "run_dashboard_watch",
]
