"""Data-plane HTTP surface (``/v1/*``).

Today this package only hosts JSON ↔ contract conversion helpers in
:mod:`nanomem.server.v1.schemas`. The actual handler wiring lives in
:mod:`nanomem.server.app`, which dispatches between the v1 data plane
and the manager control plane.

Keep this surface **small and stable** — agent harnesses talk to it
and any breaking change ripples through plugin ecosystems.
"""

from __future__ import annotations

from nanomem.server.v1.schemas import (
    capture_request_from_json,
    capture_request_to_json,
    capture_result_from_json,
    capture_result_to_json,
    flush_request_from_json,
    flush_request_to_json,
    flush_result_from_json,
    flush_result_to_json,
    read_request_from_json,
    read_request_to_json,
    read_result_from_json,
    read_result_to_json,
)

__all__ = [
    "capture_request_from_json",
    "capture_request_to_json",
    "capture_result_from_json",
    "capture_result_to_json",
    "flush_request_from_json",
    "flush_request_to_json",
    "flush_result_from_json",
    "flush_result_to_json",
    "read_request_from_json",
    "read_request_to_json",
    "read_result_from_json",
    "read_result_to_json",
]
