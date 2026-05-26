"""LLM-backed memory unit extractor.

Sub-modules:

- :mod:`nanomem.pipeline.representation.llm.extractor` — :class:`LLMMemoryUnitExtractor`
- :mod:`nanomem.pipeline.representation.llm.client`    — :class:`LLMCompletionClient`
                                                          Protocol + OpenAI reference impl
- :mod:`nanomem.pipeline.representation.llm.parsing`   — payload schema + transform

The extractor's contract: **one Dialogue is one extraction unit.** No
internal chunking. Caller decides dialogue boundaries via capture and
flush.

Prompt text lives in :mod:`nanomem.pipeline.representation.prompts`
(re-imported here for ``from nanomem.pipeline.representation.llm import
LLM_EXTRACTION_PROMPT`` back-compat).
"""

from __future__ import annotations

from nanomem.pipeline.representation.llm.client import (
    LLMCompletionClient,
    OpenAIChatCompletionClient,
)
from nanomem.pipeline.representation.llm.extractor import LLMMemoryUnitExtractor
from nanomem.pipeline.representation.llm.parsing import LLMExtractionPayloadError
from nanomem.pipeline.representation.prompts import (
    ALLOWED_MEMORY_TYPES,
    LLM_EXTRACTION_PROMPT,
    LLM_EXTRACTION_PROMPT_VERSION,
)


__all__ = [
    "ALLOWED_MEMORY_TYPES",
    "LLMCompletionClient",
    "LLMExtractionPayloadError",
    "LLMMemoryUnitExtractor",
    "LLM_EXTRACTION_PROMPT",
    "LLM_EXTRACTION_PROMPT_VERSION",
    "OpenAIChatCompletionClient",
]
