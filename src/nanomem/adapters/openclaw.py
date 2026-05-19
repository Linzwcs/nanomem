from __future__ import annotations

from nanomem.adapters.agent import AgentMemoryAdapter


class OpenClawMemoryAdapter(AgentMemoryAdapter):
    """OpenClaw-style hook adapter backed by NanoMem capture/read."""
