from __future__ import annotations

import asyncio

from nanomem.core.contracts import (
    CaptureRequest,
    CaptureResult,
    FlushRequest,
    FlushResult,
    ReadRequest,
    ReadResult,
)
from nanomem.service.core import NanoMemService


class AsyncNanoMemService:
    """Async facade for agent runtimes and ASGI servers.

    The first implementation delegates to the synchronous service in a worker
    thread. Calls are serialized because the current store and in-memory index
    are a single-node implementation, not a concurrent distributed backend.
    """

    def __init__(self, service: NanoMemService | None = None) -> None:
        self.service = service or NanoMemService()
        self._lock = asyncio.Lock()

    async def capture(self, request: CaptureRequest) -> CaptureResult:
        async with self._lock:
            return await asyncio.to_thread(self.service.capture, request)

    async def read(self, request: ReadRequest) -> ReadResult:
        async with self._lock:
            return await asyncio.to_thread(self.service.read, request)

    async def flush(self, request: FlushRequest | None = None) -> FlushResult:
        async with self._lock:
            return await asyncio.to_thread(self.service.flush, request)
