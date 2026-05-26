"""Stdlib HTTP server exposing the agent-facing v1 surface and the
control-plane manager UI.

Sub-packages:

- :mod:`nanomem.server.v1`      — data plane JSON ↔ contracts helpers
- :mod:`nanomem.server.manager` — manager UI routes and asset serving

Top-level :mod:`nanomem.server.app` wires both into one stdlib
``ThreadingHTTPServer``.
"""

from __future__ import annotations

from nanomem.transports.http.app import NanoMemHTTPServer, make_handler
from nanomem.transports.http.schemas import (
    capture_request_from_json,
    capture_result_to_json,
    read_request_from_json,
    read_result_to_json,
)

__all__ = [
    "NanoMemHTTPServer",
    "capture_request_from_json",
    "capture_result_to_json",
    "make_handler",
    "read_request_from_json",
    "read_result_to_json",
]
